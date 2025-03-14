#!/bin/bash

# Set the target directory
CACHE_DIR="$HOME/.cache/ms-playwright"

# Check if the cache directory exists
if [ ! -d "$CACHE_DIR" ]; then
  echo "Cache directory '$CACHE_DIR' not found. Exiting."
  exit 1
fi

# Navigate to the cache directory
cd "$CACHE_DIR" || {
  echo "Failed to navigate to '$CACHE_DIR'. Exiting."
  exit 1
}

# Loop through directories in the cache directory
find . -maxdepth 1 -type d -print0 | while IFS= read -r -d $'\0' dir; do
  # Extract directory name (remove leading "./")
  dirname=$(basename "$dir")

  # Exclude .links directories and the current directory itself (.)
  if [[ "$dirname" != "." ]] && [[ "$dirname" != ".links" ]]; then
    # Create the DEPENDENCIES_VALIDATED file inside the directory
    touch "$dir/DEPENDENCIES_VALIDATED"
    echo "Created DEPENDENCIES_VALIDATED in '$dir'"
  fi
done

echo "Script finished."

exit 0
