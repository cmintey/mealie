<template>
    <v-bottom-navigation>
        <template v-for="nav in links">
        <v-btn :key="nav.title">
            <span>{{ nav.title }}</span>
            <v-icon>{{ nav.icon }}</v-icon>
        </v-btn>
        </template>
        <template v-if="more.length > 0">
        <!-- <v-btn>
            <span> More </span>
            <v-icon>{{ $globals.icons.dotsHorizontal }}</v-icon>
        </v-btn> -->
        <v-menu offset-y>
            <template #activator="{ on, attrs}">
                <v-btn v-bind="attrs" v-on="on">
                    <span> More </span>
                    <v-icon>{{ $globals.icons.dotsHorizontal }}</v-icon>
                </v-btn>
            </template>
            <v-list nav dense class="my-0 py-0">
                <template v-for="nav in more">
                <v-list-item :key="nav.title" :to="nav.to">
                    <v-list-item-icon>
                  <v-icon>
                    {{ nav.icon }}
                  </v-icon>
                </v-list-item-icon>
                <v-list-item-content>
                  <v-list-item-title>
                    {{ nav.title }}
                  </v-list-item-title>
                </v-list-item-content>
                </v-list-item>
                </template>
            </v-list>
        </v-menu>
        </template>
    </v-bottom-navigation>
</template>

<script lang="ts">
import { defineComponent } from "@nuxtjs/composition-api";
import { SidebarLinks } from "~/types/application-types";

export default defineComponent({
    props: {
        topLink: {
            type: Array as () => SidebarLinks,
            required: true,
        }
    },
    setup(props) {
        return {
            links: props.topLink.slice(0, 3),
            more: props.topLink.slice(3)
        }
    }
})
</script>
