-- 将已存在的 HTML / HTM 文档的 conversion_type 从 STRUCTURED_TO_MD(3) 迁移为 HTML_TO_MD(8)
-- 使用前请先备份数据库。
-- 在 psql 或其他 SQL 客户端中执行：\i scripts/migrate_html_conversion_type.sql

BEGIN;
-- 可选：查看将受影响的记录数量
SELECT COUNT(*) AS to_update
FROM documents
WHERE file_type IN ('html','htm') AND conversion_type = 3;

-- 执行更新
UPDATE documents
SET conversion_type = 8
WHERE file_type IN ('html','htm') AND conversion_type = 3;

-- 验证：统计新类型数量
SELECT COUNT(*) AS updated_html_docs
FROM documents
WHERE file_type IN ('html','htm') AND conversion_type = 8;

COMMIT;

-- 如果需要回滚，可手动执行：
-- UPDATE documents SET conversion_type = 3 WHERE file_type IN ('html','htm') AND conversion_type = 8;