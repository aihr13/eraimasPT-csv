# Windows / WSL Containerのエージェント環境

`ai-agent-container-main/` のApple Container版を元に、WindowsのWSL標準 `wslc` とVS Code Dev Containersで開く構成。参照元のファイルは変更していない。

## 引き継いだ機能

| 項目 | Windows版の構成 |
| --- | --- |
| ベース | `node:22-bookworm`。CPUアーキテクチャはホストに合わせる |
| エージェント | Codex CLI、Ollama CLI、Antigravity CLI (`agy`)、追加済みのClaude Code |
| 開発ツール | AppleContainer版と同じpnpm、Git / Git LFS、GitHub CLI、Pythonなど |
| プロジェクト | 開いたWindowsフォルダを `/workspace` に共有 |
| 実行ユーザー | 起動時の初期化はroot、VS Codeとターミナルは `node` |
| Ollama | Windowsのサーバーに `http://host.wslc.internal:11434` で接続 |
| 接続先の制限 | コンテナ内では接続先を限定しない。Windowsやネットワーク側の制限は引き続き適用される |
| 権限 | `wslc` の標準権限で起動。未対応の `--cap-add` は使用しない |

名前付きボリュームに以下を保存する。コンテナを作り直しても残る。

| コンテナ内の場所 | ボリューム名 |
| --- | --- |
| `/home/node/.codex` | `eraimasbase-codex` |
| `/home/node/.npm` | `eraimasbase-npm` |
| `/home/node/.local/share/pnpm/store` | `eraimasbase-pnpm-store` |
| `/home/node/.gemini` | `eraimasbase-antigravity` |

Windowsのホームディレクトリや既存の認証情報は、この設定ではマウントしない。Dev Containersが追加するマウント・認証連携は別途VS Codeの設定に従う。

## Windows側の準備

1. コマンドプロンプトで `wsl --version` と `wslc version` を確認する。参考記事と同じ一般提供版を使う場合はWSL 3.0.1以降。更新が必要なら `wsl --update` を実行する。
2. Windows版VS CodeにMicrosoftの **Dev Containers** 拡張機能をインストール・更新する。
3. VS Codeの**ユーザー設定**で **Dev > Containers: Docker Path** を `wslc` に変更する。既存の設定JSONに追加する場合は次の項目を使う。

```json
"dev.containers.dockerPath": "wslc",
"dev.containers.executeInWSL": false
```

この項目はワークスペース設定ではなくユーザー設定に書く。Composeは使わない。

**Dev > Containers: Execute In WSL** はオフにする。`wslc.exe` はWindows側から実行する。ここがオンだと、通常のWSLディストリビューション（Ubuntuなど）で `wslpath` によるパス変換が走り、コンテナを起動する前に失敗する場合がある。

4. Windows側でOllamaを起動し、`http://127.0.0.1:11434/api/tags` が応答することを確認する。モデルのダウンロード・推論はWindows側が担当し、コンテナ内ではOllamaサーバーを起動しない。

WSL Containerのホストループバック名を使うため、Apple版のRosetta導入やDNSエイリアス登録は不要。

## 起動と確認

1. Windows版VS Codeで `C:\Users\aihara_yu\Documents\eraImasBase` を開く。
2. **Dev Containers: Reopen in Container** を実行する。以前の構成で作成済みなら **Dev Containers: Rebuild and Reopen in Container** を使う。
3. コンテナ内のVS Codeターミナルで確認する。

```bash
whoami
pwd
git status --short
codex --version
agy --version
pnpm store path
curl --fail --max-time 10 "$OLLAMA_HOST/api/tags"
ollama list
```

ユーザーが `node`、作業場所が `/workspace` となり、Windowsと同じファイル・Gitの変更が見えれば共有できている。Ollamaへの接続が失敗する場合は、Windows側の起動状態と `getent ahostsv4 host.wslc.internal` を確認する。

Codexは元の構成と同じく、コンテナ内で `ollama launch codex` を実行してWindows側のOllama経由で利用する。Antigravityは `agy` で起動する。

## wslcの権限とファイアウォール

`wslc 3.0.1` は `--cap-add` に未対応で、指定するとコンテナ作成時に停止する。また、コンテナ内のrootも `NET_ADMIN` 権限を持たないため、`iptables` によるファイアウォール設定は権限不足で失敗する。

`wslc` が対応するまでの一時措置として、`--cap-add` と起動時のファイアウォール初期化をコメントアウトしている。接続先をGitHub・npm・Google関連などに限定する元版のルールは適用しない。Windowsのファイアウォール設定は変更しない。

`containerScripts/init-firewall.sh` はそのまま残し、Dockerfileのコピー・権限設定・sudo設定もコメントアウトで保持している。イメージにはコピーせず実行もしない。

対応後は、`devcontainer.json` の `runArgs`、Dockerfileのファイアウォール用 `COPY` と `RUN`、`containerScripts/entrypoint.sh` の初期化呼び出しのコメントを解除する。Dockerfileの暫定的な `RUN chmod 0755 /usr/local/bin/entrypoint.sh` は元の `RUN` と重複するため削除し、コンテナを再ビルドする。オプションの対応だけでなく、コンテナ内で `NET_ADMIN` を付与できることも確認する。

Codexの承認・サンドボックス設定は変更していない。内側のLinuxサンドボックスがコンテナの権限で動くかは実行環境に依存するため、起動後に確認する。

## 元の構成からの変更

- Appleの `container` コマンドによる起動を、Dev Containersの標準起動に置き換えた。
- `host.container.internal` の固定IPを、WSL Containerのホストループバック名に置き換えた。
- 対話Bashに固定していたENTRYPOINTを、Dev Containersから渡された起動コマンドを実行する形にした。
- `wslc` に未対応の `--cap-add` と、権限不足で失敗するファイアウォール初期化を一時的にコメントアウトした。
- 既存の変更であるClaude Codeのインストールと、Codexのバージョン指定解除を維持している。
- WindowsのGit設定に影響されないよう、追加したLinux用スクリプトの改行をLFに固定する。

Emueraの起動・動作確認はWindows側で行う。コンテナで編集したERB/ERHを同じWindowsフォルダのEmueraが読み込む。

## 参考

- [今回の構成の参考記事](https://dev.classmethod.jp/articles/connect-vscode-wslc/)
- [Microsoft: WSL container](https://learn.microsoft.com/en-us/windows/wsl/wsl-container)
- [Microsoft WSL: ホストループバック名の解決報告](https://github.com/microsoft/WSL/issues/41769)
- [VS Code: Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)
- [VS Code: 必要な通信先](https://code.visualstudio.com/docs/setup/network)
- [OpenAI: Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [OpenAI: 認証](https://learn.chatgpt.com/docs/auth)
- [OpenAI: 承認とサンドボックス](https://learn.chatgpt.com/docs/agent-approvals-security)
- [Ollama: Codex連携](https://docs.ollama.com/integrations/codex)
- [Google: Antigravity CLIのインストール](https://www.antigravity.google/docs/cli/install/)
