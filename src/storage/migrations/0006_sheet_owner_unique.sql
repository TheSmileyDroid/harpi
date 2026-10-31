CREATE UNIQUE INDEX sheet_files_one_live_per_owner
    ON sheet_files (campaign, owner_id)
    WHERE owner_id IS NOT NULL
      AND status IN ('pendente', 'ativo');
