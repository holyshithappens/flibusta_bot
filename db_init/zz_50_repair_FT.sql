-- Перестроить FULLTEXT индексы
REPAIR TABLE libbook_fts QUICK;
OPTIMIZE TABLE libbook_fts;

REPAIR TABLE libaannotations QUICK;
OPTIMIZE TABLE libaannotations;

REPAIR TABLE libbannotations QUICK;
OPTIMIZE TABLE libbannotations;
