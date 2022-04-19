# ##### BEGIN GPL LICENCE BLOCK #####
#  Copyright (C) 2022  Arthur Langlard
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# ##### END GPL LICENCE BLOCK #####


# Author: Arthur Langlard, arthur.langlard@universite-paris-saclay.fr
# Start of the project: 15-04-2022
# Last modification: 15-04-2022
#
# This software is a plugin for the Veusz software.



from veusz.plugins import ImportPlugin, importpluginregistry









class ImportECLAB_CV(ImportPlugin):
    name = "EC-LAB CV"
    author = "Arthur Langlard"
    description = "Imports cyclic voltammetry measurements from EC-LAB files."
    descriptor = "Cyclic Voltammetry\n"

    # Comment this line to remove the tab of the plugin
    promote_tab = 'EC-LAB CV'
    file_extensions = set(['.mpt', '.MPT'])

    class HeaderInfo:
        m_header_lines = []
        m_header_names_str = ['Reference electrode :',
                              'Electrode surface area :',
                              'Characteristic mass :',
                              'dE/dt',
                              'dE/dt unit',
                              ]

        m_header_names = ["reference_electrode",
                          "surface",
                          "mass",
                          "scan_rate",
                          "scan_rate_unit",
                          "offset_voltage_vs_SHE",
                          "surface_unit",
                          "mass_unit",
                          ]

        m_header_string = ""

        m_header_infos = {}

        def __init__(self, header_lines):
            self.m_header_lines = header_lines
            self.m_header_string = ''.join(self.m_header_lines)
            extracted_parameters = []

            for name in self.m_header_names_str:
                extracted_parameters.append(self.extract_parameter_from_string(name).strip())

            index_of_offset_voltage = [i for i, _ in enumerate(extracted_parameters[0]) if extracted_parameters[0].startswith("(", i)][-1]
            offset_voltage_vs_SHE = float(extracted_parameters[0][index_of_offset_voltage + 1: -2].replace(",", "."))
            ref_electrode_str = extracted_parameters[0][:index_of_offset_voltage - 1]
            surface, surface_unit = extracted_parameters[1].split(" ")
            surface = float(surface.replace(",", "."))
            mass, mass_unit = extracted_parameters[2].split(" ")
            mass = float(mass.replace(",", "."))
            scan_rate = float(extracted_parameters[3].replace(",", "."))
            scan_rate_unit = extracted_parameters[4]

            parameters = [ref_electrode_str,
                          surface,
                          mass,
                          scan_rate,
                          scan_rate_unit,
                          offset_voltage_vs_SHE,
                          surface_unit,
                          mass_unit,
                          ]

            self.m_header_infos = dict(zip(self.m_header_names, parameters))

        def extract_parameter_from_string(self, name):
            for line in self.m_header_lines:
                if name in line:
                    return line.rstrip().split(name)[-1]





    def parse_header_data(self, file):
        """ Separate the file into the header part and the data part.
        """

        output = [None,None]
        flag_Is_correct_file = (file.readline() == "EC-Lab ASCII FILE\n")
        if not flag_Is_correct_file:
            raise ValueError('Not a EC-LAB file.')
        
        

        if flag_Is_correct_file:

            line = ''
            prevLine = ''
            line_no = 1 # The first line (no. 0) has already been read.
            header_lines = []
            data_lines = []

            while not "Nb header lines" in line: # Search for the length of the header.
                line = file.readline()
                line_no += 1
            length_header = int(line.split(":")[-1])

            file.readline()
            line_no += 1
            if not (file.readline() == self.descriptor):
                raise ValueError('Not a Cyclic Voltammetry file.')
            else:
                header_lines.append(self.descriptor)
            line_no += 1

            while line_no < length_header - 1:    # Parse the header.
                header_lines.append(file.readline())
                line_no += 1

            while not line == '':   # Parse the data part.
                line = file.readline()
                data_lines.append(line)
                line_no += 1

            data_lines.pop()    # Remove the last empty string.

            output = header_lines, data_lines
        return output





    def split_cycles(self, data_header, data_Np, do_split=False):
        import numpy as np
        cycle_index = data_header.index("cycle number")
        cycle_no = int(data_Np[0, cycle_index])

        if not do_split:
            return [data_header], [data_Np]

        else:

            #     Cycle 1          ,      Cycle 2 ...
            # [[point, point, ...] , [point, point, ...]]
            Cycles = [[]]
            cycles_nos = [cycle_no]

            for data_point in data_Np:
                if int(data_point[cycle_index]) == cycle_no:
                    Cycles[cycle_no - 1].append(list(data_point))
                else:
                    Cycles.append([list(data_point)])
                    cycle_no += 1
                    cycles_nos.append(cycle_no)

            Cycles_np = []
            Data_headers = []

            for cycle_list, cycle_no in zip(Cycles, cycles_nos):
                Cycles_np.append(np.array(cycle_list, dtype=float))
                header_with_cycle_no = [str(name) + " (" + str(cycle_no) + ")" for name in data_header]
                Data_headers.append(header_with_cycle_no)

        return Data_headers, Cycles_np





    def __init__(self):
        from veusz.plugins import ImportPlugin
        from veusz.plugins import ImportFieldCheck

        ImportPlugin.__init__(self)
        self.fields = [
            ImportFieldCheck("extract_cycles", descr="Import cycles as separate datasets."),
            ImportFieldCheck("import_all_data", descr="Import misc. data."),
            ]




    def import_dataset(self, params):
        import numpy as np

        f = params.openFileWithEncoding()
        try:
            header_lines, data_lines = self.parse_header_data(f)
        except ValueError:
            raise

        data_header = data_lines[0].split('\t')[:-1]    # Remove the last character (end of line '\n').
        lines_list = []
        for line in data_lines[1:]:
            lines_list.append(line.replace(',', '.').split('\t'))

        data_Np = np.array(lines_list, dtype=float)

        if not params.field_results["import_all_data"]:
            misc_data = ['mode',
                        'ox/red',
                        'error',
                        'control changes',
                        'counter inc.',
                        'I Range',
                        ]

            misc_data_indices = [data_header.index(misc_item) for misc_item in misc_data]
            data_header = [name for name in data_header if name not in misc_data]
            data_Np = np.delete(data_Np, misc_data_indices, axis=1)
        
        MyHeader = self.HeaderInfo(header_lines)

        return MyHeader, data_header, data_Np



    def getPreview(self, params):
        import numpy as np
        try:
            MyHeader, data_header, data_Np = self.import_dataset(params)
        except ValueError:
            return ("File cannot be displayed", False)

        header_string = MyHeader.m_header_string
        data_header_string = '\t'.join(data_header)
        data_string = "\n"
        max_data_len = 20
        if len(data_Np) < max_data_len:
            max_data_len = len(data_Np) - 1
        for data_line in data_Np[:max_data_len]:
            for value in data_line:
                data_string = data_string + "{:.4e}".format(value) + "\t"
            data_string = data_string + "\n"

        return (header_string + data_header_string + data_string, True)



    def doImport(self, params):
        from veusz.plugins import ImportDataset1D
        import numpy as np
        """Actually imports data.
        params is a ImportPluginParams object.
        Return a list of ImportDataset1D objects.
        """

        MyHeader, data_header, data_Np = self.import_dataset(params)


        # Add generated values to the data table.
        surface = MyHeader.m_header_infos["surface"]
        mass = MyHeader.m_header_infos["mass"]
        intensity_index = data_header.index("<I>/mA")
        charge_index = data_header.index("(Q-Qo)/C")
        dataset_i_per_surface = np.array([intensity / surface for intensity in data_Np[:, intensity_index] ])
        dataset_Q_per_mass = np.array([charge / mass for charge in data_Np[:, charge_index] ])

        data_header.append("<I>_per_surf/mA/" + MyHeader.m_header_infos["surface_unit"])
        data_Np = np.c_[data_Np, dataset_i_per_surface]
        data_header.append("(Q-Qo)_per_mass/C/" + MyHeader.m_header_infos["mass_unit"])
        data_Np = np.c_[data_Np, dataset_Q_per_mass]
        data_header.append("(Q-Qo)/mA.h")
        data_Np = np.c_[data_Np, np.array([charge / 3.6 for charge in data_Np[:, charge_index] ])]
        data_header.append("(Q-Qo)_per_mass/mA.h/" + MyHeader.m_header_infos["mass_unit"])
        data_Np = np.c_[data_Np, np.array([charge / 3.6 for charge in dataset_Q_per_mass ])]
        generated_datasets_single_values = [ImportDataset1D("mass/" + MyHeader.m_header_infos["mass_unit"],
                                              mass),
                                          ImportDataset1D("surface/" + MyHeader.m_header_infos["surface_unit"],
                                                          surface),
                                          ImportDataset1D("scan_rate/" + MyHeader.m_header_infos["scan_rate_unit"],
                                                          MyHeader.m_header_infos["scan_rate"]),
                                          ImportDataset1D("offset_voltage/VvsNHE",
                                                          MyHeader.m_header_infos["offset_voltage_vs_SHE"]),
                                          ]



        # Split data into separate cyles.
        Data_headers, Cycles_np = self.split_cycles(data_header, data_Np, params.field_results["extract_cycles"])
        imported_datasets = []

        for data_header, data_Np in zip(Data_headers, Cycles_np):
            labeled_datasets = zip(data_header, data_Np.T)
            imported_datasets = imported_datasets + [ImportDataset1D(*data) for data in labeled_datasets]


        return imported_datasets + generated_datasets_single_values


























class ImportECLAB_GC(ImportPlugin):
    name = "EC-LAB GC"
    author = "Arthur Langlard"
    description = "Imports galvanostatic cycling measurements from EC-LAB files."
    descriptor = "Galvanostatic Cycling with Potential Limitation\n"


    # Comment this line to remove the tab of the plugin
    promote_tab = 'EC-LAB GC'
    file_extensions = set(['.mpt', '.MPT'])

    class HeaderInfo:
        m_header_lines = []
        m_header_names_str = ['Reference electrode :',
                              'Electrode surface area :',
                              'Characteristic mass :',
                              'Is',
                              'unit Is',
                              'EM (V)',
                              ]

        m_header_names = ["reference_electrode",
                          "surface",
                          "mass",
                          "currents",
                          "currents_units",
                          "threshold_voltages",
                          "offset_voltage_vs_SHE",
                          "surface_unit",
                          "mass_unit",
                          ]

        m_header_string = ""

        m_header_infos = {}

        def __init__(self, header_lines):
            self.m_header_lines = header_lines
            self.m_header_string = ''.join(self.m_header_lines)
            extracted_parameters = []

            for name in self.m_header_names_str:
                extracted_parameters.append(self.extract_parameter_from_string(name).strip())

            index_of_offset_voltage = [i for i, _ in enumerate(extracted_parameters[0]) if extracted_parameters[0].startswith("(", i)][-1]
            offset_voltage_vs_SHE = float(extracted_parameters[0][index_of_offset_voltage + 1: -2].replace(",", "."))
            ref_electrode_str = extracted_parameters[0][:index_of_offset_voltage - 1]
            surface, surface_unit = extracted_parameters[1].split(" ")
            surface = float(surface.replace(",", "."))
            mass, mass_unit = extracted_parameters[2].split(" ")
            mass = float(mass.replace(",", "."))


            currents = [float(current) for current in extracted_parameters[3].replace(",", ".").split()]
            currents_units = extracted_parameters[4].split()

            threshold_voltages = [float(current) for current in extracted_parameters[5].replace(",", ".").split()]

            parameters = [ref_electrode_str,
                          surface,
                          mass,
                          currents,
                          currents_units,
                          threshold_voltages,
                          offset_voltage_vs_SHE,
                          surface_unit,
                          mass_unit,
                          ]

            self.m_header_infos = dict(zip(self.m_header_names, parameters))

        def extract_parameter_from_string(self, name):
            for line in self.m_header_lines:
                if name in line:
                    return line.rstrip().split(name)[-1]





    def parse_header_data(self, file):
        """ Separate the file into the header part and the data part.
        """

        output = [None,None]
        flag_Is_correct_file = (file.readline() == "EC-Lab ASCII FILE\n")
        if not flag_Is_correct_file:
            raise ValueError('Not a EC-LAB file.')
        
        

        if flag_Is_correct_file:

            line = ''
            prevLine = ''
            line_no = 1 # The first line (no. 0) has already been read.
            header_lines = []
            data_lines = []

            while not "Nb header lines" in line: # Search for the length of the header.
                line = file.readline()
                line_no += 1
            length_header = int(line.split(":")[-1])

            file.readline()
            line_no += 1
            if not (file.readline() == self.descriptor):
                raise ValueError('Not a Galvanostatic Cycling file.')
            else:
                header_lines.append(self.descriptor)

            line_no += 1

            while line_no < length_header - 1:    # Parse the header.
                header_lines.append(file.readline())
                line_no += 1

            while not line == '':   # Parse the data part.
                line = file.readline()
                data_lines.append(line)
                line_no += 1

            data_lines.pop()    # Remove the last empty string.

            output = header_lines, data_lines
        return output





    def split_by_variable(self, data_header, data_Np, cycling_index, do_split=False):
        import numpy as np
        cycle_no = int(data_Np[0, cycling_index])

        if not do_split:
            return [data_header], [data_Np]

        else:

            #     Cycle 1          ,      Cycle 2 ...
            # [[point, point, ...] , [point, point, ...]]
            Cycles = [[]]
            cycles_nos = [cycle_no]

            for data_point in data_Np:
                if int(data_point[cycling_index]) == cycle_no:
                    Cycles[-1].append(list(data_point))
                else:
                    Cycles.append([list(data_point)])
                    cycle_no += 1
                    cycles_nos.append(cycle_no)
            
            Cycles_np = []
            Data_headers = []

            for cycle_list, cycle_no in zip(Cycles, cycles_nos):
                Cycles_np.append(np.array(cycle_list, dtype=float))
                header_with_cycle_no = [str(name) + " (" + str(cycle_no) + ")" for name in data_header]
                Data_headers.append(header_with_cycle_no)

        return Data_headers, Cycles_np





    def __init__(self):
        from veusz.plugins import ImportPlugin
        from veusz.plugins import ImportFieldCheck

        ImportPlugin.__init__(self)
        self.fields = [
            ImportFieldCheck("extract_cycles", descr="Import cycles as separate datasets."),
            ImportFieldCheck("extract_steps", descr="Import steps as separate datasets."),
            ImportFieldCheck("import_all_data", descr="Import misc. data."),
            
            ]




    def import_dataset(self, params):
        import numpy as np

        f = params.openFileWithEncoding()
        try:
            header_lines, data_lines = self.parse_header_data(f)
        except ValueError:
            raise

        data_header = data_lines[0].split('\t')[:-1]    # Remove the last character (end of line '\n').
        lines_list = []
        for line in data_lines[1:]:
            lines_list.append(line.replace(',', '.').split('\t'))

        data_Np = np.array(lines_list, dtype=float)

        if not params.field_results["import_all_data"]:
            misc_data = ['mode',
                        'ox/red',
                        'error',
                        'control changes',
                        'Ns changes',
                        'Ns',
                        'counter inc.',
                        'I Range',
                        'dq/mA.h',
                        'control/V/mA',
                        'control/V',
                        'control/mA',
                        ]
            if not params.field_results["extract_steps"]:
                 misc_data = misc_data + ['half cycle']

            misc_data_indices = [data_header.index(misc_item) for misc_item in misc_data]
            data_header = [name for name in data_header if name not in misc_data]
            data_Np = np.delete(data_Np, misc_data_indices, axis=1)

        MyHeader = self.HeaderInfo(header_lines)
        return MyHeader, data_header, data_Np



    def getPreview(self, params):
        import numpy as np
        try:
            MyHeader, data_header, data_Np = self.import_dataset(params)
        except ValueError:
            return ("File cannot be displayed", False)


        header_string = MyHeader.m_header_string
        data_header_string = '\t'.join(data_header)
        data_string = "\n"
        max_data_len = 20
        if len(data_Np) < max_data_len:
            max_data_len = len(data_Np) - 1
        for data_line in data_Np[:max_data_len]:
            for value in data_line:
                data_string = data_string + "{:.4e}".format(value) + "\t"
            data_string = data_string + "\n"

        return (header_string + data_header_string + data_string, True)



    def doImport(self, params):
        from veusz.plugins import ImportDataset1D
        import numpy as np
        """Actually imports data.
        params is a ImportPluginParams object.
        Return a list of ImportDataset1D objects.
        """

        MyHeader, data_header, data_Np = self.import_dataset(params)


        # Add generated values to the data table.
        mass = MyHeader.m_header_infos["mass"]
        surface = MyHeader.m_header_infos["surface"]
        capacity_index = data_header.index("Capacity/mA.h")
        dataset_Q_per_mass = np.array([capacity / mass for capacity in data_Np[:, capacity_index] ])

        data_header.append("Capacity_per_mass/mA.h/" + MyHeader.m_header_infos["mass_unit"])
        data_Np = np.c_[data_Np, dataset_Q_per_mass]

        generated_datasets_single_values = [ImportDataset1D("mass/" + MyHeader.m_header_infos["mass_unit"],
                                              mass),
                                          ImportDataset1D("surface/" + MyHeader.m_header_infos["surface_unit"],
                                                          surface),
                                          ImportDataset1D("offset_voltage/VvsNHE",
                                                          MyHeader.m_header_infos["offset_voltage_vs_SHE"]),
                                          ]



        Data_headers = [data_header]
        Cycles_np = [data_Np]

        # Split data into separate cyles.
        if params.field_results["extract_steps"]:
            cycling_index_for_steps = data_header.index('half cycle')
            Data_headers, Cycles_np = self.split_by_variable(data_header, data_Np, cycling_index_for_steps, params.field_results["extract_steps"])


        D_h_temp = []
        C_np_temp = []

        Data_headers_b = []
        Cycles_np_b = []

        if params.field_results["extract_cycles"]:
            cycling_index_for_cycles = data_header.index('cycle number')
            for data_header, data_Np in zip(Data_headers, Cycles_np):
            
                D_h_temp, C_np_temp = self.split_by_variable(data_header, data_Np, cycling_index_for_cycles, params.field_results["extract_cycles"])
                Data_headers_b = Data_headers_b + D_h_temp
                Cycles_np_b = Cycles_np_b + C_np_temp

            Data_headers, Cycles_np = Data_headers_b, Cycles_np_b



        #Data_headers, Cycles_np = self.split_by_variable(data_header, data_Np, params.field_results["extract_cycles"])
        imported_datasets = []

        for data_header, data_Np in zip(Data_headers, Cycles_np):
            labeled_datasets = zip(data_header, data_Np.T)
            imported_datasets = imported_datasets + [ImportDataset1D(*data) for data in labeled_datasets]


        return imported_datasets + generated_datasets_single_values

# add the classes to the registry.
importpluginregistry.append(ImportECLAB_CV)
importpluginregistry.append(ImportECLAB_GC)
