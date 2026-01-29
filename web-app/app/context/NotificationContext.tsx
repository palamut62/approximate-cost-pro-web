"use client";

import React, { createContext, useContext, useState, useCallback } from 'react';

type NotificationType = 'success' | 'error' | 'info' | 'warning';

interface Notification {
    id: string;
    message: string;
    type: NotificationType;
}

interface ConfirmOptions {
    title?: string;
    message: string;
    onConfirm: () => void;
    onCancel?: () => void;
}

interface NotificationContextType {
    showNotification: (message: string, type?: NotificationType) => void;
    notifications: Notification[];
    removeNotification: (id: string) => void;
    confirm: (options: ConfirmOptions) => void;
    confirmState: ConfirmOptions | null;
    closeConfirm: () => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [confirmState, setConfirmState] = useState<ConfirmOptions | null>(null);

    const removeNotification = useCallback((id: string) => {
        setNotifications(prev => prev.filter(n => n.id !== id));
    }, []);

    const showNotification = useCallback((message: string, type: NotificationType = 'info') => {
        const id = Math.random().toString(36).substring(2, 9);
        setNotifications(prev => [...prev, { id, message, type }]);

        // Auto remove after 5 seconds
        setTimeout(() => {
            removeNotification(id);
        }, 5000);
    }, [removeNotification]);

    const confirm = (options: ConfirmOptions) => {
        setConfirmState(options);
    };

    const closeConfirm = () => {
        setConfirmState(null);
    };

    return (
        <NotificationContext.Provider value={{
            showNotification,
            notifications,
            removeNotification,
            confirm,
            confirmState,
            closeConfirm
        }}>
            {children}
        </NotificationContext.Provider>
    );
}

export function useNotification() {
    const context = useContext(NotificationContext);
    if (context === undefined) {
        throw new Error('useNotification must be used within a NotificationProvider');
    }
    return context;
}
