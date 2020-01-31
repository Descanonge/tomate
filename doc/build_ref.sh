#!/bin/bash


source="source"
tmp="$source/_tmp"

ref_folder="_references"
ref="$tmp/$ref_folder"
ref_final="$source/$ref_folder"

gen="$ref/autosummary"


if [ ! -d "$ref_final" ]; then
    mkdir "$ref_final"
fi

sphinx-apidoc -fMe \
    -t "$source/_templates/apidoc" \
    -o "$ref" ../data_loader

files=("$ref"/*.rst)
file="${files[0]}"
file="$(realpath "$file" --relative-to="$ref")"
package="$(echo "$file" | cut -d. -f1)"

sphinx-autogen \
    -t "$source/_templates" \
    -o "$gen" \
    "$ref/"*.rst

files=("$gen"/*.rst)
echo "Found ${#files[@]} files"
modules=""
for f in "${files[@]}"; do
    last=${f%*.rst}
    last=${last##*.}
    modules="$modules $last"
done
modules=($modules)

echo "Found modules:" "${modules[@]}"

pack=""
for m in "${modules[@]}"; do
    for f in "${files[@]}"; do
        file=${f%*.rst}
        if [[ "$file" == *"$m."* ]]; then
            pack="$pack $m"
        fi
    done
done

pack=($pack $package)
pack=($(printf "%s\n" "${pack[@]}" | sort -u))
echo "Found subpackages:" "${pack[@]}"

for f in "${files[@]}"; do
    move=0
    for p in "${pack[@]}"; do
        if [[ "$f" == *".$p.rst" ]]; then
            move=1
        fi
    done
    file=$(realpath "$f" --relative-to="$gen")
    if [[ "$move" == "0" ]]; then
        echo "move $file to $ref"
        mv "$f" "$ref/"
    else
        echo "combine $file"
        sta="$(cat "$gen/$file")"
        end="$(tail -n +2 "$ref/$file")"
        printf "%s\n\n%s" "$sta" "$end" > "$ref/$file"
    fi
done

sta=$(cat "$source/$package.rst")
end=$(tail -n +2 "$ref/$package.rst")
printf "%s\n\n%s" "$sta" "$end" > "$ref/$package.rst"

echo "Removing $ref/modules.rst"
rm "$ref/modules.rst"

files=("$ref"/*.rst)
for f in "${files[@]}"; do
    file="$(realpath "$f" --relative-to="$ref")"
    f_old="$ref_final/$file"
    if [ -f "$f_old" ]; then
        if [[ ! -z "$(diff "$f_old" "$f")" ]]; then
            echo "Updated $file"
            mv "$f" "$f_old"
        fi
    else
        echo "New file $file"
        mv "$f" "$f_old"
    fi
done

echo "Removing tmp"
rm -r "$tmp"
