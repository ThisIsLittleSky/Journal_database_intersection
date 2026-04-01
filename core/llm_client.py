# -*- coding: utf-8 -*-
import json
from urllib import error, request


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 90):
        self.base_url = (base_url or '').rstrip('/')
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _build_endpoint(self) -> str:
        if self.base_url.endswith('/chat/completions'):
            return self.base_url
        if self.base_url.endswith('/v1'):
            return self.base_url + '/chat/completions'
        return self.base_url + '/chat/completions'

    def chat_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
        payload = {
            'model': self.model,
            'temperature': temperature,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
        }
        data = json.dumps(payload).encode('utf-8')
        req = request.Request(
            self._build_endpoint(),
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            },
            method='POST',
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                response_data = json.loads(resp.read().decode('utf-8'))
        except error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='ignore')
            raise RuntimeError('LLM请求失败：' + body) from exc
        except error.URLError as exc:
            raise RuntimeError('LLM连接失败：' + str(exc)) from exc

        content = (
            response_data.get('choices', [{}])[0]
            .get('message', {})
            .get('content', '')
        )
        if not content:
            raise RuntimeError('LLM返回内容为空')
        return _extract_json(content)


def _extract_json(text: str) -> dict:
    clean_text = text.strip()
    if clean_text.startswith('```'):
        lines = clean_text.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        clean_text = '\n'.join(lines).strip()

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        start = clean_text.find('{')
        end = clean_text.rfind('}')
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError('LLM返回的不是有效JSON')
        return json.loads(clean_text[start:end + 1])
