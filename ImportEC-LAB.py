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
    description = "Imports cyclovoltammetric measurements from EC-LAB files."

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


        m_header_infos = {}

        def __init__(self, header_lines):
            self.m_header_lines = header_lines
            extracted_parameters = []

            for name in self.m_header_names_str:
                extracted_parameters.append(self.extract_parameter_from_string(name).strip())

            index_of_offset_voltage = \
                [i for i, _ in enumerate(extracted_parameters[0]) if extracted_parameters[0].startswith("(", i)][-1]
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

    
    def doImport(self, params):
        from veusz.plugins import ImportDataset1D
        import numpy as np
        """Actually imports data.
        params is a ImportPluginParams object.
        Return a list of ImportDataset1D objects.
        """
        f = params.openFileWithEncoding()

        header_lines, data_lines = self.parse_header_data(f)
        data_header = data_lines[0].split('\t')[:-1]    # Remove the last character (end of line '\n').
        lines_list = []
        for line in data_lines[1:]:
            lines_list.append(line.replace(',', '.').split('\t')[:-1])

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


        Data_headers, Cycles_np = self.split_cycles(data_header, data_Np, params.field_results["extract_cycles"])
        imported_datasets = []

        for data_header, data_Np in zip(Data_headers, Cycles_np):
            labeled_datasets = zip(data_header, data_Np.T)
            imported_datasets = imported_datasets + [ImportDataset1D(*data) for data in labeled_datasets]


        MyHeader = self.HeaderInfo(header_lines)
        surface = MyHeader.m_header_infos["surface"]
        mass = MyHeader.m_header_infos["mass"]
        intensity_index = data_header.index("<I>/mA")
        charge_index = data_header.index("(Q-Qo)/C")
        dataset_i_per_surface = np.array([intensity / surface for intensity in list(data_Np[:, intensity_index])])
        dataset_Q_per_mass = np.array([charge / mass for charge in list(data_Np[:, charge_index])])

        generated_datasets = [ImportDataset1D("<I>_per_surf/mA/"+MyHeader.m_header_infos["surface_unit"],
                                              dataset_i_per_surface),
                              ImportDataset1D("(Q-Qo)_per_mass/C/" + MyHeader.m_header_infos["mass_unit"],
                                              dataset_Q_per_mass),
                              ImportDataset1D("(Q-Qo)/mA.h",
                                              np.array([charge /3.6 for charge in list(data_Np[:, charge_index])])),
                              ImportDataset1D("(Q-Qo)_per_mass/mA.h/" + MyHeader.m_header_infos["mass_unit"],
                                              np.array([charge /3.6 for charge in list(dataset_Q_per_mass)])),
                              ImportDataset1D("mass/" + MyHeader.m_header_infos["mass_unit"],
                                              mass),
                              ImportDataset1D("surface/" + MyHeader.m_header_infos["surface_unit"],
                                              surface),
                              ImportDataset1D("scan_rate/" + MyHeader.m_header_infos["scan_rate_unit"],
                                              MyHeader.m_header_infos["scan_rate"]),
                              ImportDataset1D("offset_voltage/VvsNHE",
                                              MyHeader.m_header_infos["offset_voltage_vs_SHE"]),
                              ]


        # Return two 1D datasets: one containing the Angle and the other containing the PSD value.
        # (PSD: Position-sensitive-detector)
        #labeled_datasets = zip(data_header, data_Np.T)
        #imported_datasets = [ImportDataset1D(*data) for data in labeled_datasets]
        #imported_datasets = [ImportDataset1D(data_header[0], data_Np[:, 0]) ]
        return imported_datasets + generated_datasets

# add the class to the registry.
importpluginregistry.append(ImportECLAB_CV)
