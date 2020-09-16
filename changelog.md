
# v2.1.0

- [2020-09-16] Add different calendar support to Time
- [2020-09-16] Add defaults to Time arguments
- [2020-09-16] Add method to add variable to filegroup easily

# v2.0.2

- [2020-09-15] Fix some computations methods
- [2020-09-15] Fix average plots

# v2.0.1

- [2020-09-15] Fix infile keyring for variables with different dimensions
- [2020-09-15] Take NetCDF dimensions missing values into account

# v2.0.0

  v2 brings a lot of change, such that the API is not retro-compatible in lot of places.
  The biggest change is that each variable data is now stored in its own array.
  Variables can now have different datatypes, dimensions, or dimensions order.
  The scopes are still managed for all variables by the database object.

  The second biggest change is the extended possibilities in the scanning process.
  Multiple scanning functions can be used. Each function can only look for any number
  of 'elements' (values, in-file index, or in-file dimensions for variables). Those
  elements can be fixed to a constant value.
  
  There are many smaller changes, mostly internal, that fix bugs and do streamlining
  in the VariablesInfo, load commands creation, data loading from file, post-loading
  functions, and data writing to file.
  Extending to other file formats should be easier, as lot of complicated operations
  are made easier to execute, or moved to file-format agnostic parts of Tomate.
  
  Overall stability has decreased, since treating multiple variables with each different
  parameters is more complicated, and at the time of release, the new version has not been
  tested in the wild as much as the first version.
  
  Automatic testing has been added. For now only a handful of critical and complex
  functions are tested.
  
  A function is added to immediately open the content of a single NetCDF file as a
  database.
  

# v1.1.0

- [2020-07-10] Get filegroup by index or name
- [2020-07-06] Fix `get_index_by_day` failing if target is last index
- [2020-06-23] Fix writing if variable is not in VI
- [2020-06-23] Add option to return python datetime
- [2020-06-16] Make filegroup and database creation easier, using db.add_filegroup.
- [2020-06-15] Fix `write_add_variable` dimensions not matching.
- [2020-06-15] Add option to select the loaded scope when adding new data.
- [2020-06-15] Add kwargs for all variable when writing.
- [2020-06-15] Fix writing of squeezed dimensions.

## v1.0.3

- [2020-06-14] Add functions to plot on multiple axes at once.

## v1.0.2

- [2020-06-12] Lowercase optional dependencies
- [2020-06-12] Update writing methods. Add keyword arguments to better control writing.
  Use load command to standardize writing.
  `write_add_variable` now support multiple filegroups.
- [2020-06-12] Use `add_filegroup` instead of `link_filegroups`
- [2020-06-12] Implement `take_complex`. Add debug messages.
- [2020-06-12] Fix netCDF `open_file`

## v1.0.1

- [2020-06-12] Make optional dependencies really optional
- [2020-06-12] Fix `subset_by_day`. Now always select whole days.
- [2020-06-11] Harmonize load, view and select methods
- [2020-06-11] FilegroupNetCDF will not overwrite files (by default)
- [2020-06-11] Fix typo in get_closest. Would crash if loc='left' and value is not present in coordinate.

# v1.0.0
