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
