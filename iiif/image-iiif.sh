echo $1
folder=$(echo $path | grep -o "^[0-9]\+")
mkdir -p $folder
wget -O $path.jpg -c "https://ci--lax.elifesciences.org/iiif/$path/full/560,/0/default.jpg"
