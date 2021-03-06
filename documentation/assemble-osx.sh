#!/bin/bash

CONFLUENCE_EXPORT="$HOME/host/Downloads/NCD"
TARGET="/tmp/export"
# NUCLEATOR_CORE="$HOME/git/47lining/github/nucleator-core"
NUCLEATOR_CORE=/Users/mchance/Projects/47Lining/Nucleator/src/nucleator-core

rm -rf $TARGET
mkdir -p $TARGET
cp -rp $NUCLEATOR_CORE/documentation/site/* $TARGET/
cp -rp $CONFLUENCE_EXPORT/* $TARGET/documentation/
cd $TARGET/documentation
find . -name "Nucleator-Documentation_*.html" -exec echo making '{}' a symlink to index.html \; -exec rm '{}' \; -exec ln -s index.html '{}' \;
cd $NUCLEATOR_CORE/documentation/reference
make clean
make all
cp *.html $TARGET/documentation
sed -i .bak 's/href="Nucleator-CLI-Reference_22053054.html"/href="nucleator.html"/g' $TARGET/documentation/index.html
sed -i .bak 's/href="Quick-Start-Guide_22052991.html"/href="nucleatorquickstart.html"/g' $TARGET/documentation/index.html
make clean
