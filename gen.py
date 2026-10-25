import base64

with open('token.pickle', 'rb') as f:
    token_bytes = f.read()
    encoded = base64.b64encode(token_bytes).decode('utf-8')
    print("\n--- BASE64 TOKEN START ---")
    print(encoded)
    print("--- BASE64 TOKEN END ---\n")