Example 10: Hybrid Monte Carlo – Molecular Dynamics (MC-MD) simulations with PySIMM
========================================================================================
by Alexander Demidov and Michael E. Fortunato

### General description of the hybrid MC-MD simulation. Modules import

The example describes the work with the pysimm app that implements the hybrid MC-MD approach. Under the "hybrid MC-MD approach" here we understand the following serial iterative set of simulations. First, the Monte Carlo (MC) simulation is performed, inserting the gas molecules into the simulation system with constant volume temperature and chemical potential of inserted species (&#956;VT). This is followed by the molecular dynamics (MD) simulation step at constant pressure, temperature and number of particles (NPT). After the MD is finished, the next step of the &#956;VT MC with the new size of the simulation box is performed, and so on.

In the pySIMM the hybrid MC-MD simulations are implemented in **apps.mc_md** application. The application in turn communicates with [Cassandra](https://cassandra.nd.edu) and [LAMMPS](http://lammps.sandia.gov)  programs through **pysimm.cassandra** and **pysimm.lmps** modules correspondingly automatically setting up the required for simulation data.

```python
from pysimm.apps import mc_md
from pysimm import system
```

The example uses the hybrid MC-MD for simulation of swelling of an IRMOF-14 metal-organic framework with pure methane. The IRMOF-14 structure is taken from the [repository](https://github.com/WMD-group/BTW-FF/tree/master/structures) of the BTW-FF project, typed with with Dreiding forcefield and saved as a .lmps file in *prepare_mof.py* file.

### Simulation system setup

To start simulations, the application should get two **pysimm.system** objects. First, *frame*, is any molecular structure that presumed to be fixed during the MC simulations, and the second, *gas1*, that represents single gas molecule to be inserted by the MC. 

```python
frame = system.read_lammps('irmof-14.lmps')
frame.forcefield = 'dreiding-lj'
gas1 = system.read_lammps('ch4.lmps')
gas1.forcefield = 'trappe/amber'
```

### Preparation of the MOF structure

This section discusses the code from the *prepare_mof.py* file.
Requirements: the script uses [pandas](https://pandas.pydata.org/) python package for data input/manipulation, if it is not installed, the script will not work.

The XYZ configuration of the IRMOF-14 unit cell is downloaded as a text stream from the [GitHub repository](https://github.com/WMD-group/BTW-FF/) of the BTW-FF project, and then reorginized to the pandas dataframe.


```python
resp = requests.get('https://raw.githubusercontent.com/WMD-group/BTW-FF/master/structures/IRMOF-14.xyz')
xyz = StringIO(resp.text)

df = pd.read_table(xyz, sep='\s+', names=['tag', 'type', 'x', 'y', 'z'], usecols=[0, 1, 2, 3, 4], skiprows=1)
```

The downloaded XYZ file contains the topology information as well; for the visualisation purposes the script  produce the standard XYZ file containing only atoms coordinates:
```python
with file('irmof-14_clean.xyz', 'w') as f:
    f.write(str(len(df)) + '\nThis is the place for the header of your XYZ file\n')
    df[['type', 'x', 'y', 'z']].to_csv(f, sep='\t', header=False, index=False)
```

Using the dataframe obtained from the downloaded file, one can setup the PySimm system adding the coordinates and bonds to the particles.

```python
s = system.System()
tmp = resp.text.encode('ascii', 'ignore').split('\n')
for line in tmp[1:-1]:
    data = line.split()
    tag, ptype, x, y, z, restof = data[:6]
    elem = re.sub('\d+', '', ptype)
    bonds = map(int, data[6:])
    p = system.Particle(tag=int(tag), elem=elem, type_name=ptype, x=float(x), y=float(y), z=float(z), bonds=bonds)
    s.particles.add(p)
```

The last step is to assign  the particles with the Dreiding forcefield parameters. This is natural to do PySimm as well: all information about forcefield parameters is in the corresponding forcefield object.

```python
f = forcefield.Dreiding()
f = forcefield.Dreiding()
o_3 = s.particle_types.add(f.particle_types.get('O_3')[0].copy())
o_r = s.particle_types.add(f.particle_types.get('O_R')[0].copy())
c_r = s.particle_types.add(f.particle_types.get('C_R')[0].copy())
zn = s.particle_types.add(f.particle_types.get('Zn')[0].copy())
h_ = s.particle_types.add(f.particle_types.get('H_')[0].copy())

for p in s.particles:
    if p.elem == 'O':
        if p.bonds.count == 4:
            p.type = o_3
        else:
            p.type = o_r
    if p.elem == 'C':
        p.type = c_r
    if p.elem == 'Zn':
        p.type = zn
    if p.elem == 'H':
        p.type = h_
```

The bond, angular, dihiedral and improper terms can be assigned automatically

```python
f.assign_btypes(s)
f.assign_atypes(s)
f.assign_dtypes(s)
f.assign_itypes(s)
```


### Simulation properties setup

Additionally the application requires two dictionaries *mc_props* and *md_props* that describe the Cassandra and LAMMPS simulation settings correspondingly. The keywords of the property dictionaries correspond to the keywords provided to the Cassandra and LAMMPS programs directely.

```python
mc_props = {'rigid_type': False,
            'max_ins': 2000,
            'Chemical_Potential_Info': -22.5037,
            'Temperature_Info': 300,
            'Run_Type': {'steps': 100},
            'CBMC_Info': {'rcut_cbmc': 2.0},
            'Simulation_Length_Info': {'run': 300000,
                                       'coord_freq': 300000,
                                       'prop_freq': 1000},
            'VDW_Style': {'cut_val': 14.0},
            'Charge_Style': {'cut_val': 14.0},
            'Property_Info': {'prop1': 'energy_total',
                              'prop2': 'pressure',
                              'prop3': 'nmols'}}

md_props = {'temp': 300,
            'pressure': {'start': 15,
                         'iso': 'iso'},
            'timestep': 1,
            'cutoff': 14.0,
            'length': 100000,
            'thermo': 1000,
            'dump': 2500,
            'np': 8, 
            'print_to_screen': False}
```

### Running the application

The application itself has two settings that are provided in the form of keyword arguments: the number of iterative loops *mcmd_niter* (default is 10) and the relative path to all simulation results *sim_folder* (default is *pwd/results*).  The call of **mc_md()** function will automatically start the MC-MD simulations.

```python
sim_result = mc_md.mc_md(gas1, frame, mcmd_niter=5, sim_folder='results',  mc_props=mc_props, md_props=md_props)
```

The application returns the **pysimm.system** object that is a dump of simulated system after the final iteration.