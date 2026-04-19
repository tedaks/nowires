"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface DialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children?: React.ReactNode;
}

interface DialogTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children?: React.ReactNode;
}

interface DialogContentProps {
  children?: React.ReactNode;
  className?: string;
}

interface DialogHeaderProps {
  children?: React.ReactNode;
  className?: string;
}

interface DialogTitleProps {
  children?: React.ReactNode;
  className?: string;
}

interface DialogDescriptionProps {
  children?: React.ReactNode;
  className?: string;
}

interface DialogFooterProps {
  children?: React.ReactNode;
  className?: string;
}

interface DialogCloseProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children?: React.ReactNode;
}

function Dialog({ open, onOpenChange, children }: DialogProps) {
  return <DialogContext.Provider value={{ open: open ?? false, onOpenChange }}>{children}</DialogContext.Provider>;
}

const DialogContext = React.createContext<{ open: boolean; onOpenChange?: (open: boolean) => void }>({
  open: false,
});

function useDialog() {
  return React.useContext(DialogContext);
}

function DialogTrigger({ children, ...props }: DialogTriggerProps) {
  const { onOpenChange } = useDialog();
  return (
    <button type="button" onClick={() => onOpenChange?.(true)} {...props}>
      {children}
    </button>
  );
}

function DialogContent({ children, className }: DialogContentProps) {
  const { open, onOpenChange } = useDialog();

  React.useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange?.(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={() => onOpenChange?.(false)} />
      <div
        className={cn(
          "relative z-50 w-full max-w-md rounded-lg border border-border bg-background p-6 shadow-lg",
          className
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

function DialogHeader({ children, className }: DialogHeaderProps) {
  return <div className={cn("mb-4 flex flex-col gap-1.5", className)}>{children}</div>;
}

function DialogTitle({ children, className }: DialogTitleProps) {
  return <h2 className={cn("text-lg font-semibold", className)}>{children}</h2>;
}

function DialogDescription({ children, className }: DialogDescriptionProps) {
  return <p className={cn("text-sm text-muted-foreground", className)}>{children}</p>;
}

function DialogFooter({ children, className }: DialogFooterProps) {
  return <div className={cn("mt-6 flex justify-end gap-2", className)}>{children}</div>;
}

function DialogClose({ children, ...props }: DialogCloseProps) {
  const { onOpenChange } = useDialog();
  return (
    <button type="button" onClick={() => onOpenChange?.(false)} {...props}>
      {children}
    </button>
  );
}

export {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
};
