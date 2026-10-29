import axios from "axios";
const apiClient = axios.create({
    baseURL: "http://85.239.40.188:8000", // - вот эту, каупук
    headers: {
        "Content-Type": "application/json",
        "accept": "application/json",
    }
});

export const api = {


    // tg_id, date, action
    setOrderTime: async (orderTime) => {
        let response = await apiClient.post("/set_order_time", orderTime);
        return response.data;
    },
    getCoffeeShops: async () => {
        let response = await apiClient.get("/coffee_shops");
        return response.data;
    },
    getCoffeeShopMenu: async (id) => {
        let response = await apiClient.get(`/menu/?id=${id}`);
        return response.data;
    },

    addToCart: async ({ tg_id, coffee_shop_id, menu_item_id, quantity }) => {
        let response = await apiClient.post("/cart", {
            tg_id,
            coffee_shop_id,
            menu_item_id,
            quantity
        });
        return response.data;
    },

    deleteFromCart: async (tg_id, order_item_id) => {
        try {
            const response = await apiClient.delete(`/cart`, {
                params: {
                    tg_id: tg_id,
                    order_item_id: order_item_id
                }
            });
            return response.data;
        } catch (error) {
            console.error("Delete cart item error:", error.response?.data || error.message);
            throw error;
        }
    },

    getCart: async (tg_id, coffee_shop_id) => {
        const response = await apiClient.get(`/cart?tg_id=${tg_id}&coffee_shop_id=${coffee_shop_id}`);
        return response.data;
    }
}
