#!/bin/bash


source="source"
ref="$source/_references"
gen="$ref/autosummary"

rm -r "$ref"

sphinx-apidoc -fMe \
    -t "$source/_templates/apidoc" \
    -o "$ref" ../data_loader

file=("$ref"/*.rst)
file="${file[0]}"
file="$(realpath $file --relative-to="$ref")"
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

echo "Found modules: ${modules[@]}"

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
echo "Found subpackages: ${pack[@]}"

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
        printf "$sta\n\n$end" > "$ref/$file"
    fi
done

sta=$(cat "$source/$package.rst")
end=$(tail -n +2 "$ref/$package.rst")
printf "$sta\n\n$end" > "$ref/$package.rst"

echo "Removing generated in $gen"
rm -r "$gen"

echo "Removing $ref/modules.rst"
rm "$ref/modules.rst"
