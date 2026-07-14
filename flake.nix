{
  description = "AddBiomechanics demo (Marimo)";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

  outputs = { nixpkgs, ... }:
    let
      systems = [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-darwin"
        "x86_64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              jq
              pyright
              ruff
              uv
            ];
            shellHook = ''
              export UV_PROJECT_ENVIRONMENT=".venv"
              export PATH="$PWD/.venv/bin:$PATH"
              export PYRIGHT_PYTHON="$PWD/.venv/bin/python"
            '';
          };
        });

      apps = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          runDemo = pkgs.writeShellApplication {
            name = "movedb-demo";
            runtimeInputs = with pkgs; [ uv tailscale ];
            text = ''
              cd "$(git rev-parse --show-toplevel)"
              exec ./run.sh
            '';
          };
        in
        {
          default = {
            type = "app";
            program = "${runDemo}/bin/movedb-demo";
          };
        });
    };
}
