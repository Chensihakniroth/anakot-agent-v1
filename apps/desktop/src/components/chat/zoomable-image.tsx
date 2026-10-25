'use client'

import { useStore } from '@nanostores/react'
import { type ComponentProps, useEffect } from 'react'

import { Dialog, DialogContent } from '@/components/ui/dialog'
import { useZoomPan } from '@/components/ui/use-zoom-pan'
import { useImageDownload } from '@/hooks/use-image-download'
import { useI18n } from '@/i18n'
import { Download, ZoomIn, ZoomOut } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { $transcriptLightbox, closeTranscriptLightbox, openTranscriptLightbox } from '@/store/transcript-lightbox'

export interface ZoomableImageProps extends ComponentProps<'img'> {
  containerClassName?: string
  slot?: string
  /** Full-resolution source for the lightbox and download. */
  zoomSrc?: string
}

export interface ImageActionCopy {
  downloadImage: string
  savingImage: string
  zoomIn: string
  zoomOut: string
  resetZoom: string
}

export function ZoomableImage({
  className,
  containerClassName,
  src,
  zoomSrc,
  alt,
  slot,
  ...props
}: ZoomableImageProps) {
  const { t } = useI18n()
  const copy = t.desktop
  const fullSrc = zoomSrc || src || ''
  const { download, saving } = useImageDownload(fullSrc)
  const openSrc = useStore($transcriptLightbox)
  const lightboxOpen = openSrc !== null && openSrc === fullSrc
  const canOpen = Boolean(src)

  return (
    <>
      <span
        className={cn('group/image relative inline-block max-w-full align-top', containerClassName)}
        data-slot={slot ?? 'aui_zoomable-image'}
      >
        <button
          aria-label={canOpen ? copy.openImage : undefined}
          className="contents"
          disabled={!canOpen}
          onClick={() => canOpen && openTranscriptLightbox(fullSrc)}
          type="button"
        >
          <img alt={alt ?? ''} className={className} src={src} {...props} />
        </button>
        {src && (
          <ImageActionButton className="group-hover/image:opacity-100" copy={copy} onClick={download} saving={saving} />
        )}
      </span>
      {src && (
        <ImageLightbox
          alt={alt}
          copy={copy}
          onClick={download}
          onOpenChange={open => (open ? openTranscriptLightbox(fullSrc) : closeTranscriptLightbox(fullSrc))}
          open={lightboxOpen}
          saving={saving}
          src={fullSrc}
        />
      )}
    </>
  )
}

export function ImageLightbox({
  alt,
  copy,
  onClick,
  onOpenChange,
  open,
  saving,
  src
}: {
  alt?: string
  copy: ImageActionCopy
  onClick: () => void
  onOpenChange: (open: boolean) => void
  open: boolean
  saving: boolean
  src: string
}) {
  const { moved, panning, ref, reset, scale, stageProps, style, zoomIn, zoomOut } = useZoomPan<HTMLImageElement>({
    enabled: open
  })

  useEffect(() => {
    if (open) {
      reset()
    }
  }, [open, reset])

  const onImageClick = () => {
    if (!moved) {
      onOpenChange(false)
    }
  }

  const cursor = scale > 1 ? (panning ? 'grabbing' : 'grab') : 'zoom-out'

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent
        bodyClassName="block overflow-visible p-0"
        chrome={
          open && (
            <div
              className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-1 rounded-full border border-border/70 bg-background/85 p-1 shadow-lg backdrop-blur"
              onClick={event => event.stopPropagation()}
              onPointerDown={event => event.stopPropagation()}
            >
              <button
                aria-label={copy.zoomOut}
                className="grid size-8 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
                disabled={scale <= 0.25}
                onClick={() => zoomOut()}
                type="button"
              >
                <ZoomOut className="size-4" />
              </button>
              <button
                aria-label={copy.resetZoom}
                className="min-w-14 rounded-full px-2 text-center text-xs font-medium tabular-nums text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                onClick={() => reset()}
                type="button"
              >
                {Math.round(scale * 100)}%
              </button>
              <button
                aria-label={copy.zoomIn}
                className="grid size-8 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
                disabled={scale >= 8}
                onClick={() => zoomIn()}
                type="button"
              >
                <ZoomIn className="size-4" />
              </button>
            </div>
          )
        }
        className="w-auto max-h-[calc(100vh-12rem)] max-w-[calc(100vw-12rem)] border-0 bg-transparent! shadow-none!"
        data-variant="media-lightbox"
        overlayClassName="bg-black/60"
        showCloseButton={false}
      >
        <div className="group/lightbox relative inline-block">
          <img
            alt={alt ?? ''}
            className={cn(
              'block max-h-[calc(100vh-12rem)] max-w-[calc(100vw-12rem)] select-none rounded-lg object-contain shadow-2xl',
              panning && 'cursor-grabbing'
            )}
            onClick={onImageClick}
            ref={ref}
            src={src}
            style={{ ...style, cursor, touchAction: 'none' }}
            {...stageProps}
          />
          <ImageActionButton
            className="group-hover/lightbox:opacity-100"
            copy={copy}
            onClick={onClick}
            saving={saving}
          />
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function ImageActionButton({
  className,
  copy,
  onClick,
  saving
}: {
  className?: string
  copy: ImageActionCopy
  onClick: () => void
  saving: boolean
}) {
  return (
    <button
      aria-label={saving ? copy.savingImage : copy.downloadImage}
      className={cn(
        'absolute right-2 top-2 grid size-8 place-items-center rounded-full border border-border/70 bg-background/80 text-muted-foreground opacity-0 shadow-sm backdrop-blur transition-opacity hover:bg-accent hover:text-foreground focus-visible:opacity-100 disabled:opacity-50',
        className
      )}
      disabled={saving}
      onClick={event => {
        event.stopPropagation()
        void onClick()
      }}
      type="button"
    >
      <Download className={cn('size-4', saving && 'animate-pulse')} />
    </button>
  )
}
