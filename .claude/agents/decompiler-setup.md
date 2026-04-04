---
name: decompiler-setup
description: Sets up the .NET decompilation environment and runs bulk decompilation of all Fidelity Trader+ assemblies. Use when starting a new decompilation session or when the app has been updated to a new version.
tools: Bash, Read, Write, Glob, Grep
model: inherit
---

You set up the .NET decompilation toolchain and extract readable C# source from Fidelity Trader+ assemblies.

## Context

Fidelity Trader+ is a **.NET 10 / C# / .NET MAUI + WinUI 3** desktop application distributed as an MSIX package via the Microsoft Store. It contains **62 first-party `Fmr.*` DLLs** plus a main `Fidelity Trader+.dll` entry point. All assemblies are standard .NET managed code — no obfuscation, no NativeAOT — making them fully decompilable to near-source-quality C#.

The goal is to extract the complete API surface, data models, and protocol implementations to inform our Python SDK (`fidelity-trader-api`).

## App Location

```
APP_DIR="C:/Program Files/WindowsApps/68D72461-B3DB-4FE2-AE47-50EF0FD7254F_4.5.1.4_x64__w2vdhxtqt7mse"
```

**IMPORTANT:** This path changes with each app version. Before running, verify the current path:
```bash
ls "/c/Program Files/WindowsApps/" | grep "68D72461"
```
Use the latest version directory found.

## Output Directory

All decompiled source goes to `~/fidelity-decomp/` with this structure:
```
~/fidelity-decomp/
├── version.txt                    # App version being decompiled
├── manifest.txt                   # DLL inventory with sizes and hashes
├── src/                           # Decompiled C# source (one dir per assembly)
│   ├── Fidelity Trader+/
│   ├── Fmr.Orders/
│   ├── Fmr.Trade/
│   ├── Fmr.Positions/
│   └── ...
├── metadata/                      # Assembly metadata exports
│   ├── types.txt                  # All exported type names
│   ├── namespaces.txt             # All namespaces
│   └── references.txt             # Inter-assembly references
└── analysis/                      # Analysis output (populated by other agents)
    ├── api-endpoints.md
    ├── data-models.md
    └── ...
```

## Step 1: Install ILSpy CLI

```bash
dotnet tool install ilspycmd -g 2>/dev/null || dotnet tool update ilspycmd -g
```

If `dotnet` is not available, check:
```bash
# Windows (Git Bash)
"/c/Program Files/dotnet/dotnet.exe" --version

# Or try the user-installed path
"$LOCALAPPDATA/Microsoft/dotnet/dotnet.exe" --version
```

If no .NET SDK is installed, inform the user they need to install it:
- Download from https://dotnet.microsoft.com/download
- Minimum version: .NET 8 SDK (ilspycmd supports .NET 8+)

## Step 2: Create Output Directory Structure

```bash
mkdir -p ~/fidelity-decomp/{src,metadata,analysis}
```

## Step 3: Record App Version and DLL Inventory

```bash
# Extract version from manifest
grep 'Version=' "$APP_DIR/AppxManifest.xml" | head -1 > ~/fidelity-decomp/version.txt

# Build DLL inventory with sizes
ls -la "$APP_DIR/"*.dll | awk '{print $5, $NF}' | sort -k2 > ~/fidelity-decomp/manifest.txt

# Count first-party vs third-party
echo "=== Summary ===" >> ~/fidelity-decomp/manifest.txt
echo "First-party (Fmr.*): $(ls "$APP_DIR/"Fmr.*.dll | wc -l) DLLs" >> ~/fidelity-decomp/manifest.txt
echo "Main app: Fidelity Trader+.dll" >> ~/fidelity-decomp/manifest.txt
echo "Total assemblies: $(ls "$APP_DIR/"*.dll | wc -l) DLLs" >> ~/fidelity-decomp/manifest.txt
```

## Step 4: Bulk Decompile First-Party Assemblies

Decompile in priority order. The most valuable assemblies for API discovery are listed first.

### Priority 1: API/Network Layer (decompile first)
```
Fmr.ApiHeader.dll          — HTTP header construction, base URLs
Fmr.SocketClient.dll       — WebSocket client implementation
Fmr.WebLogin.dll           — Authentication flow
Fmr.BepsAlertStreaming.dll — Alert streaming (GraphQL)
Fmr.Sirius.dll             — Platform core (likely has HTTP client setup)
```

### Priority 2: Business Domain (bulk of API endpoints)
```
Fmr.Orders.dll             — Order placement/management (1.5MB)
Fmr.Trade.dll              — Trade execution (2.7MB)
Fmr.MloTrade.dll           — Multi-leg option trading (937KB)
Fmr.Positions.dll          — Position management (1.2MB)
Fmr.Balances.dll           — Balance/margin data (515KB)
Fmr.Quote.dll              — Quote services (1MB)
Fmr.OptionChain.dll        — Option chain data (651KB)
Fmr.OptionSummary.dll      — Option position summaries
Fmr.Watchlist.dll          — Watchlist management
Fmr.Alerts.dll             — Alert subscriptions
Fmr.Scanner.dll            — Stock/option screeners
Fmr.Research.dll           — Research data
Fmr.News.dll               — News feeds
Fmr.Chart.dll              — Chart data
Fmr.AccountHistory.dll     — Transaction history
Fmr.Accounts.dll           — Account information
Fmr.ClosedPositions.dll    — Closed position history
Fmr.TimeAndSales.dll       — Time & Sales data
Fmr.VirtualBook.dll        — L2 depth of book
Fmr.Ticker.dll             — Ticker/streaming display
Fmr.Financing.dll          — Margin/financing
Fmr.ShortInsights.dll      — Short interest data
Fmr.SpecificShares.dll     — Tax lot selection
Fmr.Preferences.dll        — User preferences
```

### Priority 3: App Shell & Framework
```
Fidelity Trader+.dll       — Main entry point, DI registration
Fmr.SuperNova.Core.dll     — App shell core
Fmr.SuperNova.Desktop.dll  — Desktop-specific shell (2.4MB)
Fmr.Nebula.dll             — Data layer (2MB)
Fmr.NovaUI.dll             — UI framework (6.4MB)
Fmr.Sirius.Maui.dll        — MAUI integration
Fmr.Architecture.Fabrics.dll — DI/service fabric
```

### Priority 4: Remaining DLLs
All other `Fmr.*.dll` files not listed above.

### Decompilation Command

For each assembly:
```bash
ilspycmd -p -o ~/fidelity-decomp/src/"$NAME" "$APP_DIR/$NAME.dll"
```

Flags:
- `-p` — Decompile to a project (creates .csproj + .cs files)
- `-o <dir>` — Output directory

For bulk decompilation, use a loop:
```bash
for dll in "$APP_DIR"/Fmr.*.dll "$APP_DIR/Fidelity Trader+.dll"; do
    name=$(basename "$dll" .dll)
    echo "Decompiling: $name"
    ilspycmd -p -o ~/fidelity-decomp/src/"$name" "$dll" 2>&1 | tail -1
done
```

**Expected time:** ~2-5 minutes for all 62 DLLs. The largest (NovaUI at 6.4MB) takes the longest.

## Step 5: Extract Metadata Index

After decompilation, build a searchable index:

```bash
# All exported types
find ~/fidelity-decomp/src -name "*.cs" -exec grep -h "^\s*public\s\+\(class\|interface\|enum\|struct\|record\)" {} \; | sort -u > ~/fidelity-decomp/metadata/types.txt

# All namespaces
find ~/fidelity-decomp/src -name "*.cs" -exec grep -h "^namespace " {} \; | sort -u > ~/fidelity-decomp/metadata/namespaces.txt

# All assembly references
find ~/fidelity-decomp/src -name "*.csproj" -exec grep -h "Reference Include" {} \; | sort -u > ~/fidelity-decomp/metadata/references.txt
```

## Step 6: Quick Validation

Verify decompilation succeeded:
```bash
# Count decompiled projects
echo "Projects: $(ls -d ~/fidelity-decomp/src/*/ | wc -l)"

# Count C# files
echo "C# files: $(find ~/fidelity-decomp/src -name '*.cs' | wc -l)"

# Count types
echo "Types: $(wc -l < ~/fidelity-decomp/metadata/types.txt)"

# Spot check: Fmr.Orders should have order-related classes
grep -c "class.*Order" ~/fidelity-decomp/metadata/types.txt
```

## Troubleshooting

### ilspycmd not found after install
```bash
export PATH="$HOME/.dotnet/tools:$PATH"
```

### Permission denied on WindowsApps
The app directory may require elevated permissions. If `ls` works but `ilspycmd` can't read:
```bash
# Copy DLLs to a temp location first
mkdir -p ~/fidelity-dlls
cp "$APP_DIR"/Fmr.*.dll ~/fidelity-dlls/
cp "$APP_DIR/Fidelity Trader+.dll" ~/fidelity-dlls/
# Then decompile from the copy
```

### Assembly load errors
Some DLLs may reference WinUI/MAUI runtime assemblies. Use `--no-dead-code` or ignore warnings — the decompiler will still output the types we need.

### .NET version mismatch
ilspycmd built for .NET 8 can decompile .NET 10 assemblies. The IL format is forward-compatible.

## Output

When complete, report:
1. App version decompiled
2. Number of assemblies successfully decompiled
3. Total C# files and types extracted
4. Any assemblies that failed (with error)
5. Top 10 largest decompiled projects by file count (these are the most complex modules)
