<script setup lang="ts">
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/quick-setup/ui/tooltip'
import { getIconVariable } from '@/lib/utils'

const DEFAULT_DELAY: number = 200
const DEFAULT_ICON: string = 'main_help'

interface ToolTipInterface {
  /** @property {number} duration - how many milliseconds should wait before displaying the tooltip  */
  delayDuration?: number

  /** @property {number} width - Height in pixels for the tooltip icon */
  width?: number

  /** @property {number} height - Height in pixels for the tooltip icon */
  height?: number

  /** @property {string} icon - URL of the icon to display */
  icon?: string
}

const props = defineProps<ToolTipInterface>()
</script>

<template>
  <TooltipProvider :delay-duration="delayDuration || DEFAULT_DELAY">
    <Tooltip>
      <TooltipTrigger as-child>
        <div class="qs-tooltip__trigger" />
      </TooltipTrigger>
      <TooltipContent as-child class="qs-tooltip__content message">
        <div>
          <slot></slot>
        </div>
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
</template>

<style scoped>
.qs-tooltip__trigger {
  display: inline-block;
  width: 16px;
  height: 16px;
  position: relative;
  top: 4px;
  background-image: v-bind('getIconVariable(props.icon || DEFAULT_ICON)');
}

.qs-tooltip__content {
  padding: 6px 12px;
  border-radius: 4px;
  line-height: 1;
  user-select: none;
  animation-duration: 400ms;
  animation-timing-function: cubic-bezier(0.16, 1, 0.3, 1);
  will-change: transform, opacity;
}
</style>
