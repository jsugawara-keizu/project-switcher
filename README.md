# project-switcher

プロジェクトフォルダをクラウドストレージとローカルワークスペース間でロード/アンロードし、Macのストレージ使用量を節約するCLIツール。

## インストール

```bash
cd /path/to/project-switcher
pipx install .
```

### タブ補完の有効化（zsh）

```bash
mkdir -p ~/.zsh/completions
~/.local/pipx/venvs/project-switcher/bin/register-python-argcomplete pswitch > ~/.zsh/completions/_pswitch
```

`~/.zshrc` に以下を追加:

```zsh
fpath=(~/.zsh/completions $fpath)
autoload -U compinit && compinit
```

## 使い方

### list — 一覧表示

```bash
pswitch list
```

ロード済み（ローカル展開中）とアンロード済み（クラウドにZip保存中）のプロジェクトを表示します。
登録済みの説明があれば `# 説明文` としてインライン表示されます。

### load — ロード

```bash
pswitch load <project> [project2 ...]
```

クラウドのZipをローカルワークスペースへ展開します。複数プロジェクトを同時に指定できます。
展開完了後、クラウド側のZipファイルは削除されます。

### unload — アンロード

```bash
pswitch unload <project> [project2 ...]
```

ローカルのプロジェクトフォルダをZip圧縮してクラウドへ移動します。複数指定可。
同名のZipが既にある場合は上書きします。ローカルフォルダは削除されます。

iCloud Drive の場合は、クラウドへの同期完了後に `brctl evict` でローカルのZipコピーを自動削除します。
evictのタイムアウト時は `iCloudへのアップロードはバックグラウンドで継続されます` と表示されますが、手動での操作は不要です。iCloudクライアントがバックグラウンドでアップロードを完了させ、自動でクラウド専用状態に移行します。

### desc — 説明の管理

```bash
pswitch desc <project> "説明文"   # 登録・更新
pswitch desc <project>            # 表示
pswitch desc <project> --delete   # 削除
```

プロジェクトごとに説明を登録します。設定ファイルに保存され、ロード/アンロード状態が変わっても引き継がれます。

### config — 設定

```bash
pswitch config                        # 現在の設定を表示
pswitch config --icloud-dir <PATH>    # クラウド側の保存先を変更
pswitch config --local-dir <PATH>     # ローカルワークスペースを変更
```

設定ファイル: `~/.config/project-switcher/config.json`

| キー | デフォルト値 | 説明 |
|------|------------|------|
| `icloud_dir` | `~/Library/Mobile Documents/com~apple~CloudDocs/Cloud Workspaces` | クラウド側のZip保存先 |
| `local_dir` | `~/Local Workspaces` | ローカルの展開先 |
| `descriptions` | `{}` | プロジェクトの説明（`desc` コマンドで管理） |

## 対応クラウドストレージ

### iCloud Drive（推奨）

追加設定不要。以下の機能が自動で動作します。

- **ロード時**: 未ダウンロード（`.icloud` プレースホルダ）のZipを `brctl download` で自動取得
- **アンロード時**: クラウドへの同期完了後に `brctl evict` でローカルのZipコピーを自動削除

### OneDrive

**事前設定**: OneDrive の設定 → アカウント → **「Files On-Demand」をオン**にする。

`pswitch unload` でZipをOneDriveフォルダに配置後、OneDriveクライアントが自動でクラウド専用状態（オンデマンド）に移行します。

```bash
pswitch config --icloud-dir "/Users/<name>/OneDrive/Cloud Workspaces"
```

### Google Drive

**事前設定**: Google Drive の設定 → **「ストリーミング」モード**を選択する。

> 「ミラーリング」モードでは全ファイルが常にローカルに保存されるため、ストレージ節約効果がありません。

`pswitch unload` でZipを配置後、Google Driveクライアントが自動でクラウド専用状態に移行します。

```bash
pswitch config --icloud-dir "/Users/<name>/Google Drive/My Drive/Cloud Workspaces"
```

## コードの更新後の再インストール

```bash
cd /path/to/project-switcher
pipx install . --force

# タブ補完スクリプトも再生成
~/.local/pipx/venvs/project-switcher/bin/register-python-argcomplete pswitch > ~/.zsh/completions/_pswitch
```
