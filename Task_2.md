
### 2. api_client.py

```python
"""
API клиент для взаимодействия с микросервисом Avito
"""

import requests
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AvitoAPIClient:
    """Клиент для работы с API Avito"""
    
    BASE_URL = "https://qa-internship.avito.com"
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or self.BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def create_item(self, name: str, price: int, seller_id: int) -> Dict[str, Any]:
        """
        Создание нового объявления
        
        Args:
            name: название объявления
            price: цена
            seller_id: ID продавца
            
        Returns:
            Dict с ответом сервера
        """
        url = f"{self.base_url}/api/1/item"
        payload = {
            "name": name,
            "price": price,
            "sellerId": seller_id
        }
        
        logger.info(f"Creating item: {payload}")
        response = self.session.post(url, json=payload)
        
        try:
            return {
                "status_code": response.status_code,
                "data": response.json() if response.text else {},
                "headers": dict(response.headers)
            }
        except ValueError:
            return {
                "status_code": response.status_code,
                "data": {"raw": response.text},
                "headers": dict(response.headers)
            }
    
    def get_item(self, item_id: str) -> Dict[str, Any]:
        """
        Получение объявления по ID
        
        Args:
            item_id: идентификатор объявления
            
        Returns:
            Dict с ответом сервера
        """
        url = f"{self.base_url}/api/1/item/{item_id}"
        
        logger.info(f"Getting item: {item_id}")
        response = self.session.get(url)
        
        try:
            return {
                "status_code": response.status_code,
                "data": response.json() if response.text else {},
                "headers": dict(response.headers)
            }
        except ValueError:
            return {
                "status_code": response.status_code,
                "data": {"raw": response.text},
                "headers": dict(response.headers)
            }
    
    def get_seller_items(self, seller_id: int) -> Dict[str, Any]:
        """
        Получение всех объявлений продавца
        
        Args:
            seller_id: ID продавца
            
        Returns:
            Dict с ответом сервера
        """
        url = f"{self.base_url}/api/1/{seller_id}/item"
        
        logger.info(f"Getting items for seller: {seller_id}")
        response = self.session.get(url)
        
        try:
            return {
                "status_code": response.status_code,
                "data": response.json() if response.text else {},
                "headers": dict(response.headers)
            }
        except ValueError:
            return {
                "status_code": response.status_code,
                "data": {"raw": response.text},
                "headers": dict(response.headers)
            }
    
    def get_item_statistic(self, item_id: str) -> Dict[str, Any]:
        """
        Получение статистики по объявлению
        
        Args:
            item_id: идентификатор объявления
            
        Returns:
            Dict с ответом сервера
        """
        url = f"{self.base_url}/api/1/statistic/{item_id}"
        
        logger.info(f"Getting statistic for item: {item_id}")
        response = self.session.get(url)
        
        try:
            return {
                "status_code": response.status_code,
                "data": response.json() if response.text else {},
                "headers": dict(response.headers)
            }
        except ValueError:
            return {
                "status_code": response.status_code,
                "data": {"raw": response.text},
                "headers": dict(response.headers)
            }
