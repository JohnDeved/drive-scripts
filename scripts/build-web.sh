#!/bin/bash
set -e
cd web
npm run build
cd ..
echo "Web GUI built successfully."
