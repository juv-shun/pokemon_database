-- movesテーブルのdamage_classをNULL許容に変更
-- キョダイマックス技などはdamage_classがNULLの場合がある

ALTER TABLE sv.moves DROP CONSTRAINT IF EXISTS chk_damage_class;
ALTER TABLE sv.moves ALTER COLUMN damage_class DROP NOT NULL;
ALTER TABLE sv.moves ADD CONSTRAINT chk_damage_class 
    CHECK (damage_class IS NULL OR damage_class IN ('physical', 'special', 'status'));
