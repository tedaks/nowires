"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Props {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

export default function FormField({ label, value, onChange }: Props) {
  return (
    <div>
      <Label className="text-xs">{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} className="h-7 text-xs" />
    </div>
  );
}