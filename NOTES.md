## conda with vscode
conda init powershell
in Windows PowerShell: Set-ExecutionPolicy Remotesigned
conda config --append channels conda-forge
conda update conda
conda config --add channels conda-forge

## install qudi
conda update --all
conda install python=3.10
conda create --name qudi-env python=3.10
conda activate qudi-env
python -m pip install qudi-core
python -m pip install git+https://github.com/fffish95/qudi-core.git@main  
# when update use python -m pip install --ignore-installed git+https://github.com/fffish95/qudi-core.git@main
python -m pip install -e .
qudi-install-kernel

# qt platform error in linux system
sudo apt-get install qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools

## install arduino-python3
conda activate qudi-env
python -m pip install --upgrade pip
python -m pip install arduino-python3

## install pythonnet
python -m pip uninstall clr
conda install -c conda-forge pythonnet

## fetch upsteam
git remote add upstream https://github.com/Ulm-IQO/qudi-iqo-modules.git
git fetch upstream
git checkout main
git rebase upstream/main
git push origin main --force

## fetch branch
git reset --hard origin/main
git fetch origin
git checkout -b feature origin/feature

## retain commit
If you want to create a new branch to retain commits you create, you may
do so (now or later) by using -c with the switch command. Example:
  git switch -c <new-branch-name>

Or undo this operation with:

  git switch -con


## install TimeTagger in linux
first install TimeTagger in general enviroment
copy TimeTagger.py and other 3 _TimeTagger files from Computer/lib/python3/dist-packages to anaconda3/envs/qudi-env/lib
copy libstdc++.so.6 from Computer/lib/x86_64-linux-gnu to anaconda3/envs/qudi-env/lib

## module 'numpy' has no attribute 'bool'
in new numpy version np.bool is changed to np.bool_
find out the function in your environment packages, change .bool to .bool_