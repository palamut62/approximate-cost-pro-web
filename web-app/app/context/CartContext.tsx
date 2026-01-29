"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';

type Poz = {
    poz_no: string;
    description: string;
    unit: string;
    unit_price: string;
    institution: string;
    source_file: string;
}

type CartContextType = {
    items: Poz[];
    addItem: (item: Poz) => void;
    removeItem: (poz_no: string) => void;
    clearCart: () => void;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export function CartProvider({ children }: { children: React.ReactNode }) {
    const [items, setItems] = useState<Poz[]>([]);

    // Load from localStorage on mount
    useEffect(() => {
        const saved = localStorage.getItem('approx_cost_cart');
        if (saved) {
            try {
                setItems(JSON.parse(saved));
            } catch (e) {
                console.error("Cart parse error:", e);
            }
        }
    }, []);

    // Save to localStorage on change
    useEffect(() => {
        localStorage.setItem('approx_cost_cart', JSON.stringify(items));
    }, [items]);

    const addItem = (item: Poz) => {
        setItems(prev => {
            // Prevent duplicates
            if (prev.some(i => i.poz_no === item.poz_no)) return prev;
            return [...prev, item];
        });
    };

    const removeItem = (poz_no: string) => {
        setItems(prev => prev.filter(i => i.poz_no !== poz_no));
    };

    const clearCart = () => setItems([]);

    return (
        <CartContext.Provider value={{ items, addItem, removeItem, clearCart }}>
            {children}
        </CartContext.Provider>
    );
}

export function useCart() {
    const context = useContext(CartContext);
    if (context === undefined) {
        throw new Error('useCart must be used within a CartProvider');
    }
    return context;
}
