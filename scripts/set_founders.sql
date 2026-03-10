-- ForGlory — Definir as 3 contas fundadoras
-- Rodar UMA VEZ no banco de produção via Neon console ou psql

-- Opção A: por ID (as primeiras 3 contas cadastradas)
UPDATE users SET role = 'fundador' WHERE id IN (1, 2, 3);

-- Opção B: por username (mais seguro — substitua os nomes)
-- UPDATE users SET role = 'fundador' WHERE username IN ('Comando', 'Shay', 'Shakadum');

-- Confirmar
SELECT id, username, role FROM users WHERE role = 'fundador' ORDER BY id;
