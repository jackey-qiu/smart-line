# How to install 
1. create virtual env using 'conda create --name img python==3.x --no-default-packages', x can be 10 9 or 7
2. python 3.10, python 3.9: cd to src folder and simply run `pip install -U .`
3. python 3.7: you need to manually install imreg-dft and trackpy from source code project,after running `pip install .`
- for imreg-dft:
  - cd to a folder which is not in the smart-line project
  - git clone https://github.com/matejak/imreg_dft.git
  - cd imreg_dft
  - python setup.py install
- for trackpy
  - cd to a folder which is not in the smart-line project 
  - git clone https://github.com/soft-matter/trackpy
  - cd trackpy
  - python setup.py develop
4. run the cmd `smart` in a terminal, you should see the main window pop up.
