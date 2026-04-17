# project-switcher

プロジェクトフォルダをクラウドストレージとローカルワークスペース間でロード/アンロードし、Macのストレージ使用量を節約するCLIツール。

## インストール

```bash
cd /path/to/project-switcher
pipx install .
```

タブ補完の有効化（zsh）:

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

```bash
pswitch list                        # ロード済み・アンロード済みの一覧表示
pswitch load <project>              # クラウド → ローカルに展開
pswitch load <project1> <project2>  # 複数同時ロード
pswitch unload <project>            # ローカル → クラウドにZip圧縮して移動
pswitch unload <project1> <project2> # 複数同時アンロード
pswitch config                      # 現在の設定を表示
pswitch config --icloud-dir <PATH>  # クラウド側の保存先を変更
pswitch config --local-dir <PATH>   # ローカルワークスペースを変更
```

## 設定

設定ファイル: `~/.config/project-switcher/config.json`

| キー | デフォルト値 | 説明 |
|------|------------|------|
| `icloud_dir` | `~/Library/Mobile Documents/com~apple~CloudDocs/Cloud Workspaces` | クラウド側のZip保存先 |
| `local_dir` | `~/Local Workspaces` | ローカルの展開先 |

## 対応クラウドストレージ

### iCloud Drive（推奨）

追加設定不要。以下の機能が自動で動作します。

- **ロード時**: 未ダウンロード（`.icloud` プレースホルダ）のZipを `brctl download` で自動取得
- **アンロード時**: iCloudへの同期完了後に `brctl evict` でローカルコピーを自動削除

### OneDrive

**事前設定**: OneDrive の設定 → アカウント → **「Files On-Demand」をオン**にする。

この設定が有効であれば、`pswitch unload` でzipをOneDriveフォルダに配置した後、OneDriveクライアントが自動でクラウド専用状態（オンデマンド）に移行します。`brctl evict` は実行されません。

```bash
pswitch config --icloud-dir "/Users/<name>/OneDrive/Cloud Workspaces"
```

### Google Drive

**事前設定**: Google Drive の設定 → **「ストリーミング」モード**を選択する。

> 「ミラーリング」モードでは全ファイルが常にローカルに保存されるため、ストレージ節約効果がありません。

`pswitch unload` でzipを配置後、Google Driveクライアントが自動でクラウド専用状態に移行します。`brctl evict` は実行されません。

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
