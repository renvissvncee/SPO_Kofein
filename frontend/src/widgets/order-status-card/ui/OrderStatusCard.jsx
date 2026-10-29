// OrderStatusCard.jsx
import './orderStatusCard.scss';

const OrderStatusCard = ({ order }) => {
    if (!order) return null;

    return (
        <div className="order-status-card">
            <div className="order-status-card__content">
                <div className="order-status-card__left">
                    <div className="order-status-card__icon">
                        <span>⏱️</span>
                    </div>
                    <div className="order-status-card__info">
                        <p className="order-status-card__shop">{order.shopName}</p>
                        <p className="order-status-card__time">{order.timeText}</p>
                    </div>
                </div>
                <div className="order-status-card__right">
                    <h3 className="order-status-card__title">Заказ принят</h3>
                </div>
            </div>
        </div>
    );
};

export default OrderStatusCard;