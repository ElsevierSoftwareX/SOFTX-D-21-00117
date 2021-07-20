from pysimm import system, lmps, forcefield

def run(test=False):
    # use a smiles string to query the pubchem search database and read the mol file returned from the http request
    try:
        s = system.read_pubchem_smiles('CO')
    except:
        import os
        s = system.read_mol(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'CO.mol'))
    
    # the resulting system has sufficient information to type with a forcefield, here we will use the Dreiding force field
    s.apply_forcefield(forcefield.Dreiding())
    
    # we'll perform energy minimization using the fire algorithm in LAMMPS
    lmps.quick_min(s, min_style='fire')
    
    # write a few different file formats
    s.write_xyz('methanol.xyz')
    s.write_yaml('methanol.yaml')
    s.write_lammps('methanol.lmps')
    s.write_chemdoodle_json('methanol.json')

if __name__ == '__main__':
    run()