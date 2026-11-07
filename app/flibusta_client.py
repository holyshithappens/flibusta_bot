import os
import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType
from urllib.parse import unquote, urlparse
import re
from bs4 import BeautifulSoup

from .constants import FLIBUSTA_BASE_URL, FLIBUSTA_ONION_URL, FLIBUSTA_TOR_PROXY


class FlibustaClient:
    _base_url: str = FLIBUSTA_BASE_URL
    _onion_url: str = FLIBUSTA_ONION_URL
    _tor_proxy: str = FLIBUSTA_TOR_PROXY

    MODE_DIRECT = "direct"
    MODE_PROXY = "proxy"
    MODE_TOR = "tor"

    def __init__(self, username, password, connection_mode: str = None):
        self._session = None
        self._auth_session = None
        self._username = username
        self._password = password
        self._is_logged_in = False

        if connection_mode is None:
            use_tor = os.getenv("FLIBUSTA_USE_TOR", "false").lower() == "true"
            self._connection_mode = self.MODE_TOR if use_tor else self.MODE_DIRECT
        else:
            self._connection_mode = connection_mode

    def set_connection_mode(self, mode: str):
        if mode in (self.MODE_DIRECT, self.MODE_PROXY, self.MODE_TOR):
            self._connection_mode = mode
            self._session = None
            self._auth_session = None
            self._is_logged_in = False
        else:
            raise ValueError(f"Invalid connection mode: {mode}")

    def get_current_base_url(self) -> str:
        if self._connection_mode == self.MODE_TOR:
            return self._onion_url
        return self._base_url

    def _get_proxy_config(self) -> dict | None:
        if self._connection_mode == self.MODE_TOR:
            proxy_url = self._tor_proxy
            parsed = urlparse(proxy_url)
            return {
                'proxy_type': ProxyType.SOCKS5,
                'host': parsed.hostname or '127.0.0.1',
                'port': parsed.port or 9050,
                'rdns': True,
                'username': parsed.username,
                'password': parsed.password,
            }
        elif self._connection_mode == self.MODE_PROXY:
            proxy_url = os.getenv("FLIBUSTA_PROXY")
            if proxy_url:
                parsed = urlparse(proxy_url)
                scheme = parsed.scheme.lower().replace('h', '')
                proxy_type_map = {
                    'socks5': ProxyType.SOCKS5,
                    'socks4': ProxyType.SOCKS4,
                    'http': ProxyType.HTTP,
                    'https': ProxyType.HTTP,
                }
                return {
                    'proxy_type': proxy_type_map.get(scheme, ProxyType.HTTP),
                    'host': parsed.hostname,
                    'port': parsed.port,
                    'rdns': False,
                    'username': parsed.username,
                    'password': parsed.password,
                }
        return None

    async def _create_session(self, auth: bool = False):
        # Longer timeouts for Tor connections
        if self._connection_mode == self.MODE_TOR:
            timeout = aiohttp.ClientTimeout(total=300, connect=60, sock_connect=60, sock_read=120)
            test_timeout = aiohttp.ClientTimeout(total=60)
        else:
            timeout = aiohttp.ClientTimeout(total=120, connect=30, sock_connect=30, sock_read=30)
            test_timeout = aiohttp.ClientTimeout(total=10)
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        proxy_config = self._get_proxy_config()
        connector = None

        if proxy_config:
            connector = ProxyConnector(
                proxy_type=proxy_config['proxy_type'],
                host=proxy_config['host'],
                port=proxy_config['port'],
                rdns=proxy_config['rdns'],
                username=proxy_config['username'],
                password=proxy_config['password'],
            )
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers,
                trust_env=False
            )
        else:
            session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                trust_env=False
            )

        try:
            test_url = self.get_current_base_url()
            async with session.get(test_url, timeout=test_timeout) as resp:
                if resp.status == 200:
                    print(f"Connection successful via {self._connection_mode}: {resp.status}")
                    return session
                else:
                    await session.close()
                    if connector:
                        await connector.close()
                    raise Exception(f"Connection test failed with status {resp.status}")
        except Exception as e:
            print(f"Connection failed via {self._connection_mode} ({e})")
            await session.close()
            if connector:
                await connector.close()
            raise

    async def _get_session(self, auth=False):
        try:
            if not auth:
                if self._session is None:
                    self._session = await self._create_session()
                async with self._session.get(self.get_current_base_url()) as resp:
                    if resp.status != 200:
                        await self._session.close()
                        self._session = await self._create_session()
                return self._session
            else:
                if self._auth_session is None or not self._is_logged_in:
                    await self.login()
                async with self._auth_session.get(self.get_current_base_url()) as resp:
                    if resp.status != 200:
                        await self.login()
                return self._auth_session
        except Exception as e:
            print(f"Connection error ({e}), recreating session...")
            if not auth:
                if self._session:
                    await self._session.close()
                self._session = await self._create_session()
                return self._session
            else:
                if self._auth_session:
                    await self._auth_session.close()
                await self.login()
                return self._auth_session

    @classmethod
    def get_cover_url_direct(cls, local_cover_url, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/ib/{local_cover_url}" if local_cover_url else None

    @classmethod
    def get_author_photo_url(cls, local_photo_url, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/ia/{local_photo_url}" if local_photo_url else None

    @classmethod
    def get_book_url(cls, book_id, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/b/{book_id}" if book_id else None

    @classmethod
    def get_download_url(cls, book_id, book_format, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/b/{book_id}/{book_format}" if book_id and book_format else None

    @classmethod
    def get_author_url(cls, author_id, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/a/{author_id}" if author_id else None

    @classmethod
    def get_translator_url(cls, translator_id, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/a/{translator_id}" if translator_id else None

    @classmethod
    def get_genre_url(cls, genre_id, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/g/{genre_id}" if genre_id else None

    @classmethod
    def get_series_url(cls, series_id, connection_mode: str = MODE_DIRECT) -> str | None:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/s/{series_id}" if series_id else None

    @classmethod
    def get_login_url(cls, connection_mode: str = MODE_DIRECT) -> str:
        base_url = cls._onion_url if connection_mode == cls.MODE_TOR else cls._base_url
        return f"{base_url}/user/login"

    async def login(self):
        try:
            if self._auth_session is None:
                self._auth_session = await self._create_session(auth=True)

            login_url = self.get_login_url(self._connection_mode)
            async with self._auth_session.get(login_url) as response:
                html = await response.text()

            form_build_id = None
            if 'form_build_id' in html:
                start = html.find('form_build_id') + len('form_build_id')
                start = html.find('value="', start) + len('value="')
                end = html.find('"', start)
                form_build_id = html[start:end]

            form_data = {
                'name': self._username,
                'pass': self._password,
                'form_id': 'user_login',
                'op': 'Вход в систему',
                'persistent_login': '1'
            }
            if form_build_id:
                form_data['form_build_id'] = form_build_id

            async with self._auth_session.post(login_url, data=form_data) as response:
                result_html = await response.text()

            self._is_logged_in = ('Выйти' in result_html) or (self._username in result_html)
            return self._is_logged_in

        except Exception as e:
            print(f"Authorization error: {e}")
            return False

    async def logout(self):
        if self._auth_session:
            await self._auth_session.close()
            self._auth_session = None
        self._is_logged_in = False

    async def download_book(self, book_id, book_format, auth=False, connection_mode: str = None):
        mode = connection_mode or self._connection_mode
        session = await self._get_session(auth)
        download_url = self.get_download_url(book_id, book_format, mode)

        try:
            async with session.get(download_url) as response:
                if response.status != 200:
                    return None, None
                book_data = await response.read()
                content_type = response.headers.get('Content-Type', '')

                if 'html' in content_type:
                    html = await response.text()
                    if 'Страница не найдена' in html:
                        return None, None

                filename = None
                cd = response.headers.get('Content-Disposition')
                if cd:
                    if m := re.search(r'filename[^;=\n]*=([\'"]?)([^\'"\n]+)\1', cd, re.IGNORECASE):
                        filename = unquote(m.group(2))
                return book_data, filename
        except Exception as e:
            print(f"Book download error: {e}")
            return None, None

    async def download_book_resilient(self, book_id, book_format, auth=False):
        modes_to_try = [
            self._connection_mode,
            self.MODE_TOR,
            self.MODE_PROXY,
            self.MODE_DIRECT
        ]

        seen = set()
        unique_modes = [m for m in modes_to_try if not (m in seen or seen.add(m))]

        for mode in unique_modes:
            try:
                book_data, filename = await self.download_book(
                    book_id, book_format, auth, connection_mode=mode
                )
                if book_data:
                    return book_data, filename
            except Exception as e:
                print(f"Download failed via {mode}: {e}")
                continue

        return None, None

    async def close(self):
        if self._session:
            await self._session.close()
        if self._auth_session:
            await self._auth_session.close()

    async def get_book_cover_url(self, book_id: str, connection_mode: str = None):
        mode = connection_mode or self._connection_mode
        try:
            url = self.get_book_url(book_id, mode)
            session = await self._get_session(auth=False)
            cover_url = await self._extract_cover_url_from_page(url, session, mode)
            if cover_url:
                return cover_url
            session = await self._get_session(auth=True)
            return await self._extract_cover_url_from_page(url, session, mode)
        except Exception as e:
            print(f"Cover retrieval error: {e}")
            return None

    async def _extract_cover_url_from_page(self, url, session, connection_mode: str = None):
        async with session.get(url) as response:
            if response.status == 200:
                html_resp = await response.text()
                soup = BeautifulSoup(html_resp, 'html.parser')
                cover_img = soup.find('img', {'title': 'Cover image'})
                if not cover_img:
                    cover_img = soup.find('img', {'alt': 'Cover image'})

                if cover_img and cover_img.get('src'):
                    cover_url = cover_img['src']
                    if not cover_url.startswith('http'):
                        mode = connection_mode or self._connection_mode
                        base = self._onion_url if mode == self.MODE_TOR else self._base_url
                        cover_url = f"{base}{cover_url}"
                    return cover_url
        return None


flibusta_client = FlibustaClient(os.getenv("FLIBUSTA_USERNAME"), os.getenv("FLIBUSTA_PASSWORD"))