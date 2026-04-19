"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface SiteNameDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  siteNameInput: string;
  onSiteNameInputChange: (value: string) => void;
  onConfirm: () => void;
}

export function SiteNameDialog({
  open,
  onOpenChange,
  siteNameInput,
  onSiteNameInputChange,
  onConfirm,
}: SiteNameDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Save Site</DialogTitle>
          <DialogDescription>Enter a name for this coverage site.</DialogDescription>
        </DialogHeader>
        <Input
          value={siteNameInput}
          onChange={(e) => onSiteNameInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onConfirm();
          }}
          placeholder="Site name"
          autoFocus
        />
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="default" onClick={onConfirm}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface ClearConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}

export function ClearConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
}: ClearConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Clear All Sites</DialogTitle>
          <DialogDescription>This will remove all saved sites from the map.</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm}>
            Clear All
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}