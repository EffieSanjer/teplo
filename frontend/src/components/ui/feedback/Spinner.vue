<script setup lang="ts">
import { LoaderCircle } from 'lucide-vue-next';

withDefaults(defineProps<{ size?: number }>(), { size: 16 });
</script>

<template>
  <LoaderCircle class="spin" :size="size" aria-hidden="true" />
</template>
