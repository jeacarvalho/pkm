#!/bin/bash
# Wrapper script to run vault indexer with proper Python path

export PYTHONPATH=/home/s015533607/Documentos/desenv/pkm
python3 -m src.indexing.vault_indexer "$@"
