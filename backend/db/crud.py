from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from .models import CoffeeShop, MenuCategory, Order, OrderItem, MenuItem, User, Favorite, get_session
import datetime
import uuid

async def get_shop_work_time(shop_id: int):
    async with get_session() as session:
        result = await session.execute(
            select(CoffeeShop).where(CoffeeShop.id == shop_id)
        )
        shop = result.scalar_one_or_none()
        if shop:
            return shop.opening_time, shop.closing_time
        return None
    
async def get_all_coffee_shops(order_time: str = None):
    async with get_session() as session:
        if order_time:
            order_time = order_time.split()
            order_time_parsed = datetime.datetime.strptime(order_time[1], '%H:%M:%S').time()
            result = await session.execute(
                select(CoffeeShop).where(
                    CoffeeShop.opening_time <= order_time_parsed,
                    CoffeeShop.closing_time >= order_time_parsed
                )
            )
        else:
            result = await session.execute(select(CoffeeShop))
        shops = result.scalars().all()
        return shops

async def get_menu_item_info(menu_item_id):
    async with get_session() as session:
        result = await session.execute(
            select(MenuItem).where(MenuItem.id == menu_item_id)
        )
        item = result.scalar_one_or_none()
        if item:
            return {
                "id": str(item.id),
                "name": item.name,
                "base_price": item.base_price,
            }
        return None

async def get_coffee_shop_menu(coffee_shop_id):
    async with get_session() as session:
        result = await session.execute(
            select(MenuCategory)
            .where(MenuCategory.coffee_shop_id == coffee_shop_id)
            .options(selectinload(MenuCategory.menu_items))
        )
        categories = result.unique().scalars().all()
        categories_data = [
            {
                "id": category.id,
                "coffee_shop_id": category.coffee_shop_id,
                "name": category.name.replace("(", "").replace(")", ""),
                "items": [
                    {
                        "id": item.id,
                        "coffee_shop_id": item.coffee_shop_id,
                        "category_id": item.category_id,
                        "name": item.name,
                        "description": item.description,
                        "base_price": item.base_price,
                        "image_url": item.image_url,
                        "is_available": item.is_available,
                        "created_at": item.created_at,
                    }
                    for item in category.menu_items
                ]
            }
            for category in categories
            if category.menu_items
        ]
        return categories_data


async def add_favorite(tg_id: int, coffee_shop_id):
    async with get_session() as session:
        # Проверяем, существует ли кофейня
        shop_result = await session.execute(
            select(CoffeeShop).where(CoffeeShop.id == coffee_shop_id)
        )
        if not shop_result.scalar_one_or_none():
            return None

        # Проверяем, не добавлена ли уже
        favorite_result = await session.execute(
            select(Favorite).where(
                Favorite.telegram_id == tg_id,
                Favorite.coffee_shop_id == coffee_shop_id,
            )
        )
        favorite = favorite_result.scalar_one_or_none()

        if favorite:
            return favorite

        new_favorite = Favorite(
            id=uuid.uuid4(),
            telegram_id=tg_id,
            coffee_shop_id=coffee_shop_id,
        )
        session.add(new_favorite)
        await session.commit()
        await session.refresh(new_favorite)

        return new_favorite


async def remove_favorite(tg_id: int, coffee_shop_id):
    async with get_session() as session:
        result = await session.execute(
            select(Favorite).where(
                Favorite.telegram_id == tg_id,
                Favorite.coffee_shop_id == coffee_shop_id,
            )
        )
        favorite = result.scalar_one_or_none()
        if not favorite:
            return False

        await session.delete(favorite)
        await session.commit()
        return True


async def get_favorites(tg_id: int):
    async with get_session() as session:
        result = await session.execute(
            select(Favorite).where(Favorite.telegram_id == tg_id).options(selectinload(Favorite.coffee_shop))
        )
        favorites = result.scalars().all()
        return [favorite.coffee_shop for favorite in favorites]


async def add_to_cart(tg_id: int, coffee_shop_id, menu_item_id, quantity: int):
    async with get_session() as session:
        # Получаем или создаём корзину пользователя для этого кофейшопа
        result = await session.execute(
            select(Order)
            .where(Order.telegram_id == tg_id)
            .where(Order.coffee_shop_id == coffee_shop_id)
            .where(Order.status == "cart")
            .options(selectinload(Order.items))
        )
        order = result.scalar_one_or_none()
        
        if not order:
            order = Order(
                id=uuid.uuid4(),
                telegram_id=tg_id,
                coffee_shop_id=coffee_shop_id,
                status="cart",
                total_amount=0,
            )
            session.add(order)
            await session.flush()
        
        # Получаем информацию о пункте меню
        menu_item_result = await session.execute(
            select(MenuItem).where(MenuItem.id == menu_item_id)
        )
        menu_item = menu_item_result.scalar_one_or_none()
        
        if not menu_item:
            return None
        
        # Проверяем, есть ли уже такой товар в корзине
        order_item_result = await session.execute(
            select(OrderItem)
            .where(OrderItem.order_id == order.id)
            .where(OrderItem.menu_item_id == menu_item_id)
        )
        order_item = order_item_result.scalar_one_or_none()
        
        # Флаг, нужно ли удалить корзину
        should_delete_order = False
        
        if order_item:
            new_quantity = order_item.quantity + quantity
            
            if new_quantity <= 0:
                # Удаляем только позицию товара
                await session.delete(order_item)
                # Проверяем, остались ли ещё товары в корзине
                remaining_items_result = await session.execute(
                    select(OrderItem).where(OrderItem.order_id == order.id)
                )
                remaining_items = remaining_items_result.scalars().all()
                
                # Если товаров не осталось, отмечаем корзину на удаление
                if not remaining_items:
                    should_delete_order = True
            else:
                # Обновляем количество
                order_item.quantity = new_quantity
                order_item.total_price = order_item.unit_price * order_item.quantity
        else:
            # Добавляем новый товар (только если quantity > 0)
            if quantity > 0:
                order_item = OrderItem(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    menu_item_id=menu_item_id,
                    quantity=quantity,
                    unit_price=menu_item.base_price,
                    total_price=menu_item.base_price * quantity,
                )
                session.add(order_item)
        
        # Если корзину нужно удалить
        if should_delete_order:
            await session.delete(order)
            await session.commit()
            return "deleted"
        
        # Получаем все товары в корзине и пересчитываем total_amount
        all_items_result = await session.execute(
            select(OrderItem).where(OrderItem.order_id == order.id).options(selectinload(OrderItem.menu_item))
        )
        all_items = all_items_result.scalars().all()
        
        # Пересчитываем общую сумму
        order.total_amount = sum(item.total_price for item in all_items)
        
        await session.commit()
        
        return {
            "id": order.id,
            "telegram_id": order.telegram_id,
            "coffee_shop_id": order.coffee_shop_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "items": [
                {
                    "id": item.id,
                    "order_id": item.order_id,
                    "menu_item_id": item.menu_item_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "product": {
                        "id": item.menu_item.id,
                        "coffee_shop_id": item.menu_item.coffee_shop_id,
                        "category_id": item.menu_item.category_id,
                        "name": item.menu_item.name,
                        "description": item.menu_item.description,
                        "base_price": item.menu_item.base_price,
                        "image_url": item.menu_item.image_url,
                        "is_available": item.menu_item.is_available,
                        "created_at": item.menu_item.created_at,
                    }
                }
                for item in all_items
            ]
        }


async def remove_from_cart(tg_id: int, order_item_id):
    """Удалить товар из корзины"""
    async with get_session() as session:
        # Получаем товар
        result = await session.execute(
            select(OrderItem).where(OrderItem.id == order_item_id).options(selectinload(OrderItem.order))
        )
        order_item = result.scalar_one_or_none()
        
        if not order_item:
            return None
        
        order_id = order_item.order_id
        coffee_shop_id = order_item.order.coffee_shop_id
        
        # Удаляем товар
        await session.delete(order_item)
        
        # Получаем оставшиеся товары в корзине
        remaining_items_result = await session.execute(
            select(OrderItem).where(OrderItem.order_id == order_id).options(selectinload(OrderItem.menu_item))
        )
        remaining_items = remaining_items_result.scalars().all()
        
        # Обновляем total_amount заказа
        total_amount = sum(item.total_price for item in remaining_items)
        
        order_update_result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_update_result.scalar_one_or_none()
        
        if order:
            order.total_amount = total_amount
        
        await session.commit()
        
        # Если товаров не осталось, возвращаем пустую корзину или None
        if not remaining_items:
            return None
        
        return {
            "id": order.id,
            "telegram_id": order.telegram_id,
            "coffee_shop_id": order.coffee_shop_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "items": [
                {
                    "id": item.id,
                    "order_id": item.order_id,
                    "menu_item_id": item.menu_item_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "product": {
                        "id": item.menu_item.id,
                        "coffee_shop_id": item.menu_item.coffee_shop_id,
                        "category_id": item.menu_item.category_id,
                        "name": item.menu_item.name,
                        "description": item.menu_item.description,
                        "base_price": item.menu_item.base_price,
                        "image_url": item.menu_item.image_url,
                        "is_available": item.menu_item.is_available,
                        "created_at": item.menu_item.created_at,
                    }
                }
                for item in remaining_items
            ]
        }


async def get_cart(tg_id: int, coffee_shop_id):
    """Получить корзину пользователя для кофейшопа"""
    async with get_session() as session:
        result = await session.execute(
            select(Order)
            .where(Order.telegram_id == tg_id)
            .where(Order.coffee_shop_id == coffee_shop_id)
            .where(Order.status == "cart")
            .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        return {
            "id": order.id,
            "telegram_id": order.telegram_id,
            "coffee_shop_id": order.coffee_shop_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "items": [
                {
                    "id": item.id,
                    "order_id": item.order_id,
                    "menu_item_id": item.menu_item_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "product": {
                        "id": item.menu_item.id,
                        "coffee_shop_id": item.menu_item.coffee_shop_id,
                        "category_id": item.menu_item.category_id,
                        "name": item.menu_item.name,
                        "description": item.menu_item.description,
                        "base_price": item.menu_item.base_price,
                        "image_url": item.menu_item.image_url,
                        "is_available": item.menu_item.is_available,
                        "created_at": item.menu_item.created_at,
                    }
                }
                for item in order.items
            ]
        }
