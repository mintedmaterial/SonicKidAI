def print_h_bar():
    """Print a horizontal bar for visual separation in logs"""
    print("─" * 80)

def format_price(price: float, decimals: int = 4) -> str:
    """Format price with proper decimal places and separators"""
    return f"${price:,.{decimals}f}"

def format_token_pair(token_in: str, token_out: str) -> str:
    """Format token pair for display"""
    return f"{token_in}/{token_out}"