
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
