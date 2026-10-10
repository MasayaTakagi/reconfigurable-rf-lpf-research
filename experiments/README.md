# 実験管理

新規実験は `EXP-NNN/config.json`、`results.json`、`summary.md` を基本とする。旧実験はGit履歴の記録として扱い、旧コードの再現性を保守しない。新規実験では共通の `src/lpf` を使い、結果を上書きせず新しいIDを発行する。
