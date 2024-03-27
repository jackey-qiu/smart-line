# smart-line


# How to install 
. create virtual env using 'conda create --name img python==3.x --no-default-packages', x can be 10 9 or 7
. python 3.10, python 3.9: simply run 'pip install -r requirements.txt'
. python 3.7: you need to manually install imreg-dft and trackpy from source code project, then run 'pip install -r requirements_py37.txt'
- for imreg-dft: 
  git clone https://github.com/matejak/imreg_dft.git
  cd imreg_dft
  python setup.py install
- for trackpy
    git clone https://github.com/soft-matter/trackpy
    cd trackpy
    python setup.py develop