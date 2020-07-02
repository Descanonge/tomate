# Version 2.0 Roadmap

Tomate manipulates multiple variables in a same big multi-dimensional array.
This is nice when you do computations accross multiple variables. Even then,
the gain of having a single array over a list of array is no that important, 
since there usually is a small number of variable.
Furthermore, this prevents from having variable with different types or variables
varying along different dimensions.

The 2.0 version aims at correcting this by manipulating one array for each variable.


# TODO

## Manipulating arrays

- [x] Add Variable class
- [~] Adapt data viewing
- [ ] Adapt data setting
- [~] Adapt data loading


## Other

- [ ] Move VI in Variable class
- [x] Store dimensions order in CoordScanVar
- [ ] Access filegroups by name rather than index
- [x] Replace tuples with classes
- [x] Turbocharge CoordScan: element specific scanning, more than
  one function of each kind (in and filename), fix one element,
  customize scanners on the fly (change the elements it scans, or
  restrain what elements will be used)
