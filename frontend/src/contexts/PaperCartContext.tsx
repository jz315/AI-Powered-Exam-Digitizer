import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";

export interface CartQuestion {
  id: string;
  content: string;
  type: string;
  options?: string[];
  difficulty?: string;
  tags?: string[];
  answer?: string;
  analysis?: string;
  sub_questions?: unknown[];
}

interface PaperCartContextType {
  cartItems: CartQuestion[];
  addToCart: (question: CartQuestion) => void;
  removeFromCart: (id: string) => void;
  clearCart: () => void;
  isInCart: (id: string) => boolean;
  cartCount: number;
  reorderCart: (oldIndex: number, newIndex: number) => void;
}

const PaperCartContext = createContext<PaperCartContextType | undefined>(undefined);

const STORAGE_KEY = "paper_cart";

export function PaperCartProvider({ children }: { children: ReactNode }) {
  const [cartItems, setCartItems] = useState<CartQuestion[]>(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        try {
          return JSON.parse(stored);
        } catch {
          return [];
        }
      }
    }
    return [];
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cartItems));
  }, [cartItems]);

  const addToCart = useCallback((question: CartQuestion) => {
    setCartItems(prev => {
      if (prev.some(q => q.id === question.id)) {
        return prev;
      }
      return [...prev, question];
    });
  }, []);

  const removeFromCart = useCallback((id: string) => {
    setCartItems(prev => prev.filter(q => q.id !== id));
  }, []);

  const clearCart = useCallback(() => {
    setCartItems([]);
  }, []);

  const isInCart = useCallback((id: string) => {
    return cartItems.some(q => q.id === id);
  }, [cartItems]);

  const reorderCart = useCallback((oldIndex: number, newIndex: number) => {
    setCartItems(prev => {
      const result = [...prev];
      const [removed] = result.splice(oldIndex, 1);
      result.splice(newIndex, 0, removed);
      return result;
    });
  }, []);

  return (
    <PaperCartContext.Provider
      value={{
        cartItems,
        addToCart,
        removeFromCart,
        clearCart,
        isInCart,
        cartCount: cartItems.length,
        reorderCart,
      }}
    >
      {children}
    </PaperCartContext.Provider>
  );
}

export function usePaperCart() {
  const context = useContext(PaperCartContext);
  if (!context) {
    throw new Error("usePaperCart must be used within PaperCartProvider");
  }
  return context;
}
