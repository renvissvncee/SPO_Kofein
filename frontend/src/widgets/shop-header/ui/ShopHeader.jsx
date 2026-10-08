import '../ui/shopHeader.scss'
import { ChevronLeft } from 'lucide-react'
import {useEffect, useState} from "react";

const ShopHeader = ({
                        shop,
                        setCurrentPage,
                        headerRef,
                        isCollapsed
                    }) => {

    const handleBack = () => {
        setCurrentPage('shops');
    };

    return (
        <div
            className={`shop-header ${isCollapsed ? 'collapsed' : ''}`}
            ref={headerRef}
        >
            <div className="shop-header__content">

                <img
                    src={shop.coffee_shop_image}
                    alt=""
                    className="shop-header__bg"
                />

                <div className="shop-header__overlay" />

                <button
                    className="shop-header__back"
                    onClick={handleBack}
                >
                    <ChevronLeft />
                </button>

                <h1 className="shop-header__title">
                    {shop.name}
                </h1>

            </div>
        </div>
    )
}

export default ShopHeader;