## conda with vscode
conda init powershell
in Windows PowerShell: Set-ExecutionPolicy Remotesigned
conda config --append channels conda-forge
conda update conda
conda config --add channels conda-forge

## install qudi
conda update --all
conda install python=3.9
conda create --name qudi-env python=3.9
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


## errors
sps_scanner cursor_position edited:

Error while closing scanner
Traceback (most recent call last):
  File "C:\Users\Venus\qudi\src\qudi\hardware\local\sps_setup.py", line 450, in close_scanner
    if not self._scanner_ai_task.is_task_done():
AttributeError: 'int' object has no attribute 'is_task_done'

