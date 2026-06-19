# Reformat the python code using ruff.
# Chris Joakim, 2026

Write-Host "========== Reformatting python code =========="
# Format all files in the current directory
ruff format  

# Format all files in `src/` (and any subdirectories).
ruff format src     

# Format all files in `tests/` (and any subdirectories).
# ruff format tests

Write-Host "========== Running pylint =========="
pylint --errors-only *.py src