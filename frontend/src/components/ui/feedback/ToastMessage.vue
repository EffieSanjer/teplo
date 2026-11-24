<script setup lang="ts">
import { ShieldCheck } from 'lucide-vue-next';

defineProps<{ message: string }>();
</script>

<template>
  <div class="toast-message" role="status"><ShieldCheck :size="18" />{{ message }}</div>
</template>
