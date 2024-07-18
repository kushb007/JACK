import requests
j = {
    "source_code": """
    public class Main {
    public static void main(String[] args) {
        System.out.println("hello, world");
    }
}
    """,
    "language_id": 62,
    "stdin": ""
}
r = requests.post('http://164.92.99.150:2358/submissions/?wait=true&base64_encoded=true',json=j)
print(r.json())