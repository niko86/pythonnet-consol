import base64
import io
from os import path

import clr
import matplotlib
matplotlib.use('Agg') # Needed to stop QT backend errors
import numpy as np
from lxml import etree
from matplotlib.figure import Figure
from matplotlib.ticker import FormatStrFormatter

from functions import (generate_xml, parse_file, parse_results, round_down, round_up)

clr.AddReference("wpf\PresentationFramework") 
from Microsoft.Win32 import OpenFileDialog, SaveFileDialog
from System import Convert, Uri, UriKind
from System.IO import MemoryStream, Path, StreamReader
from System.Threading import ApartmentState, Thread, ThreadStart
from System.Windows import Application, LogicalTreeHelper, Window
from System.Windows.Markup import XamlReader
from System.Windows.Media import Imaging

dir_path = path.dirname(__file__)
xaml_path = 'MainWindow.xaml'

class MyWindow(Window):
    def __init__(self):
        try:
            stream = StreamReader(xaml_path)
            self.window = XamlReader.Load(stream.BaseStream)
            self.initialise_icon()
            self.initialise_elements()
            self.initialise_visibility()
            Application().Run(self.window)  
            
        except Exception as ex:
            print(ex)

    def initialise_elements(self):
        """
        Formerly used:
        self.FileComboBox = LogicalTreeHelper.FindLogicalNode(self.window, "FileComboBox")
        self.FileComboBox.IsEnabled = False
        self.FileComboBox.SelectionChanged += self.FileComboBox_SelectionChanged
        """
        root = etree.parse('MainWindow.xaml').getroot()
        ns = root.nsmap
        data = [(etree.QName(i).localname, i.attrib['Name']) for i in root.findall(".//*[@Name]", ns)]

        for tag, attr in data:
            self.__setattr__(attr, LogicalTreeHelper.FindLogicalNode(self.window, f"{attr}"))
            if tag == 'Button':
                self.__getattribute__(attr).Click += self.__getattribute__(f"{attr}_Click")
            if tag == 'ComboBox':
                self.__getattribute__(attr).SelectionChanged += self.__getattribute__(f"{attr}_SelectionChanged")

    def initialise_icon(self):
        icon_uri = Uri(dir_path + "/" + "program_icon.png", UriKind.Absolute)
        self.window.Icon = Imaging.BitmapImage(icon_uri)

    def initialise_visibility(self):
        self.OpenFileButton.IsEnabled = True
        self.SaveXMLButton.IsEnabled = False
        self.FileComboBox.IsEnabled = False

    def combo_clear(self):
        self.FileComboBox.Items.Clear()

    def log_append(self, msg):
        self.LogTextBox.AppendText(msg + '\n')

    def log_clear(self):
        self.LogTextBox.Clear()

    def clear_plot(self):
        self.PlotImage.Source = None

    def generate_plot(self, x, y, title):
        fig = Figure()
        axes = fig.add_subplot(111)

        new_y = [value*0.001 for value in y]
        displacement = round(max(new_y) - min(new_y), 3)

        axes.plot(x, new_y, marker='.') 
        axes.set_title(title)
        axes.set_xlabel("Time (mins)")
        axes.set_ylabel("Gauge Reading (mm)")
        axes.set_xlim(min(x), round_up(max(x), decimals=-2))
        axes.set_ylim(round_down(min(new_y), decimals=1), max(new_y))
        axes.yaxis.set_major_formatter(FormatStrFormatter('%.2f')) 

        self.log_clear()
        self.log_append(f"   Displacement = {displacement}mm")
        self.log_append(f"   Max Gauge Reading = {max(y)}")
        self.log_append(f"   Min Gauge Reading = {min(y)}")
        self.log_append(f"   Gauge Reading Diff = {max(y)-min(y)}")
        self.log_append(f"   Time Taken = {int(max(x))} min")

        return fig

    def set_plot(self, fig):
        base64string = base64_fig(fig)
        imagebytes = Convert.FromBase64String(base64string)
        image = stream_bitmap(imagebytes)
        self.PlotImage.Source = image

    def OpenFileButton_Click(self, sender, e):
        dlg = OpenFileDialog()
        dlg.DefaultExt = ".txt"
        dlg.Filter = "Text Files (*.txt)|*.txt"
        dlg.Multiselect = True

        if dlg.ShowDialog() == True:
            self.file_names = dlg.FileNames
            self.combo_clear()
            self.log_clear()
            self.log_append(f'Successfully loaded {len(self.file_names)} stages:')

            for file_name in self.file_names:
                stem = Path.GetFileNameWithoutExtension(file_name)
                self.log_append(stem)
                self.FileComboBox.Items.Add(stem)

            self.SaveXMLButton.IsEnabled = True
            self.FileComboBox.IsEnabled = True

    def FileComboBox_SelectionChanged(self, sender, e):
        self.clear_plot()

        if self.FileComboBox.SelectedIndex != -1:
            comboIndex = self.FileComboBox.SelectedIndex
            file_name = self.file_names[comboIndex]
            data = parse_file(file_name)
            stem = Path.GetFileNameWithoutExtension(file_name)
            fig = self.generate_plot(
                    x = data['Stage_StageReadings_StagePasteMins1'],
                    y = data['Stage_StageReadings_StagePasteDive1'],
                    title = stem,
                )
            self.set_plot(fig)


    def SaveXMLButton_Click(self, sender, e):
        dlg = SaveFileDialog()
        dlg.Filter = "XML file (*.xml)|*.xml"
        dlg.FilterIndex = 2
        dlg.RestoreDirectory = True

        if dlg.ShowDialog() == True:
            file_name = dlg.FileName
            try:
                with open(file_name, 'wb') as file:
                    results = parse_results(self.file_names)
                    xml = generate_xml(results)
                    file.write(xml)

                self.SaveXMLButton.IsEnabled = False
                self.log_clear()
                self.log_append("XML successfully created.")
            except IOError:
                print("Cannot save current data to file.")

def base64_fig(plt):
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200)
    buf.seek(0)
    py_base64string = str(base64.b64encode(buf.read()))
    return py_base64string[2:-1]

def stream_bitmap(imagebytes):
    memoryStream = MemoryStream(imagebytes)
    memoryStream.Position = 0
    image = Imaging.BitmapImage()
    image.BeginInit()
    image.StreamSource = memoryStream
    image.CacheOption = Imaging.BitmapCacheOption.OnLoad
    image.EndInit()
    return image

if __name__ == '__main__':
    thread = Thread(ThreadStart(MyWindow))
    thread.SetApartmentState(ApartmentState.STA)
    thread.Start()
    thread.Join()
