import { useState, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Upload, 
  Image as ImageIcon,
  X, 
  Check, 
  Loader2
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface FileUploaderProps {
  onSuccess?: (fileData: {
    filename: string;
    originalname: string;
    mimetype: string;
    size: number;
    path: string;
  }) => void;
  accept?: string;
  maxSize?: number; // in bytes
  title?: string;
  description?: string;
}

export function FileUploader({
  onSuccess,
  accept = "image/*",
  maxSize = 5 * 1024 * 1024, // 5MB
  title = "Upload a file",
  description = "Drag and drop or click to upload"
}: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  
  const inputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const resetState = () => {
    setFile(null);
    setPreview(null);
    setError(null);
    setSuccess(false);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  const validateFile = (file: File): boolean => {
    // Check file type
    if (!file.type.match(accept.replace('*', ''))) {
      setError(`File type not supported. Please upload ${accept} files.`);
      return false;
    }

    // Check file size
    if (file.size > maxSize) {
      setError(`File too large. Maximum size is ${maxSize / 1024 / 1024}MB.`);
      return false;
    }

    return true;
  };

  const handleFile = (file: File) => {
    setError(null);
    setSuccess(false);
    
    if (!validateFile(file)) {
      return;
    }

    setFile(file);
    
    // Create preview for images
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a file first");
      return;
    }

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('image', file);

    try {
      const response = await fetch('/api/uploads/image', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Upload failed');
      }

      setSuccess(true);
      toast({
        title: "Upload successful",
        description: "Your file has been uploaded successfully.",
      });

      // Call onSuccess callback with file data
      if (onSuccess && result.data) {
        onSuccess(result.data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      toast({
        variant: "destructive",
        title: "Upload failed",
        description: err instanceof Error ? err.message : 'An error occurred during upload.',
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Card className="p-6 w-full">
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-medium">{title}</h3>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>

        {/* Upload area */}
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`
            border-2 border-dashed rounded-lg p-6 cursor-pointer 
            flex flex-col items-center justify-center space-y-2
            transition-colors
            ${isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/20 hover:border-primary/50'}
            ${error ? 'border-destructive bg-destructive/5' : ''}
            ${success ? 'border-green-500 bg-green-500/5' : ''}
          `}
        >
          <Input
            ref={inputRef}
            type="file"
            accept={accept}
            onChange={handleInputChange}
            className="hidden"
          />

          {preview ? (
            <div className="relative w-full max-w-xs">
              <img 
                src={preview} 
                alt="Preview" 
                className="w-full h-auto max-h-48 object-contain rounded-md"
              />
              <Button
                type="button"
                size="icon"
                variant="destructive"
                className="absolute top-2 right-2 h-6 w-6 rounded-full"
                onClick={(e) => {
                  e.stopPropagation();
                  resetState();
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <>
              {success ? (
                <div className="h-12 w-12 rounded-full bg-green-500/20 flex items-center justify-center">
                  <Check className="h-6 w-6 text-green-500" />
                </div>
              ) : (
                <div className="h-12 w-12 rounded-full bg-primary/20 flex items-center justify-center">
                  {isUploading ? (
                    <Loader2 className="h-6 w-6 text-primary animate-spin" />
                  ) : (
                    <Upload className="h-6 w-6 text-primary" />
                  )}
                </div>
              )}
              <div className="text-center space-y-1">
                <p className="text-sm font-medium">
                  {isUploading ? 'Uploading...' : success ? 'Upload complete!' : 'Drag file here or click to browse'}
                </p>
                <p className="text-xs text-muted-foreground">
                  Supports {accept.replace('*', 'all')} files up to {maxSize / 1024 / 1024}MB
                </p>
              </div>
            </>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="text-sm text-destructive">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end space-x-2">
          <Button
            type="button"
            variant="outline"
            onClick={resetState}
            disabled={isUploading || (!file && !preview)}
          >
            Reset
          </Button>
          <Button
            type="button"
            onClick={handleUpload}
            disabled={isUploading || !file || success}
          >
            {isUploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : success ? (
              <>
                <Check className="mr-2 h-4 w-4" />
                Uploaded
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload
              </>
            )}
          </Button>
        </div>
      </div>
    </Card>
  );
}