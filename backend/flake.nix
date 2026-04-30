{
  description = "InfraLens backend (FastAPI + Python)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python311;
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python
            uv

            # Native deps for psycopg[binary], snowflake-connector, cryptography
            openssl
            postgresql.lib
            libffi
            zlib
            stdenv.cc.cc.lib
          ];

          shellHook = ''
            export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
              pkgs.openssl
              pkgs.postgresql.lib
              pkgs.libffi
              pkgs.zlib
              pkgs.stdenv.cc.cc.lib
            ]}:$LD_LIBRARY_PATH"

            if [ ! -d .venv ]; then
              echo "Creating virtualenv..."
              uv venv --python ${python}/bin/python .venv
            fi

            source .venv/bin/activate

            if [ ! -f .venv/.installed ] || [ pyproject.toml -nt .venv/.installed ]; then
              echo "Installing dependencies..."
              uv pip install -r requirements.txt --quiet
              touch .venv/.installed
            fi

            echo "Backend environment ready. Run: uv run uvicorn app.main:app --reload --port 8000"
          '';
        };
      });
}
