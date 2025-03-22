#!/bin/bash

while true
do
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
    echo "Rebooting in:"
    for i in 12 11 10 9 8 7 6 5 4 3 2 1
    do
        echo "$i..."
        sleep 1
    done
    echo "Rebooting now!"
done
