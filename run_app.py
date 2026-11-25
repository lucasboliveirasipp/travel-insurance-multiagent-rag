"""Entry point da aplicação Streamlit."""

import sys
from pathlib import Path

# Configurar path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    import streamlit.web.cli as stcli
    
    # Executar Streamlit
    sys.argv = ["streamlit", "run", "agent.py"]
    sys.exit(stcli.main())

