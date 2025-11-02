-- pokemon_movesテーブルからnotesカラムを削除
-- 習得方法の情報は保存せず、ポケモンと技の関連のみを管理する

ALTER TABLE sv.pokemon_moves DROP COLUMN IF EXISTS notes;
